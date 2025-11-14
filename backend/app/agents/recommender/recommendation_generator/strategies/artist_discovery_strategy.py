"""Strategy for generating recommendations from mood-matched artists."""

import structlog
from typing import Any, Dict, List, Optional

from ....tools.reccobeat_service import RecoBeatService
from ....tools.spotify_service import SpotifyService
from ....states.agent_state import AgentState, TrackRecommendation
from ...utils import TrackRecommendationFactory
from ..handlers.artist_pipeline import ArtistRecommendationPipeline
from .base_strategy import RecommendationStrategy

logger = structlog.get_logger(__name__)


class ArtistDiscoveryStrategy(RecommendationStrategy):
    """Strategy for generating recommendations from mood-matched artists discovered from user listening history."""

    def __init__(
        self,
        reccobeat_service: RecoBeatService,
        spotify_service: SpotifyService
    ):
        """Initialize the artist discovery strategy.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
        """
        super().__init__("artist_discovery")
        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service

        # Use shared pipeline (with failed artist caching)
        self.pipeline = ArtistRecommendationPipeline(
            spotify_service=spotify_service,
            reccobeat_service=reccobeat_service,
            use_failed_artist_caching=True
        )

    async def generate_recommendations(
        self,
        state: AgentState,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate recommendations from mood-matched artists.

        Args:
            state: Current agent state
            target_count: Target number of recommendations to generate

        Returns:
            List of recommendation data dictionaries
        """
        # Use shared pipeline with our recommendation creation logic
        return await self.pipeline.process_artists(
            state=state,
            create_recommendation_fn=self._create_recommendation_wrapper,
            calculate_score_fn=self._calculate_artist_track_score
        )

    async def _create_recommendation_wrapper(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        audio_features_map: Dict[str, Dict[str, Any]],
        calculate_score_fn: callable
    ) -> Optional[TrackRecommendation]:
        """Wrapper to adapt _create_artist_track_recommendation to pipeline signature.

        Args:
            track: Track data from Spotify
            target_features: Target mood features
            audio_features_map: Pre-fetched audio features
            calculate_score_fn: Function to calculate score

        Returns:
            TrackRecommendation object or None if filtered out
        """
        return await self._create_artist_track_recommendation(track, target_features, audio_features_map)

    async def _create_artist_track_recommendation(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        audio_features_map: Dict[str, Dict[str, Any]]
    ) -> Any:
        """Create a recommendation from an artist track.

        Args:
            track: Track data from Spotify
            target_features: Target mood features
            audio_features_map: Pre-fetched audio features for all tracks

        Returns:
            TrackRecommendation object or None if filtered out
        """
        # Spotify returns tracks with 'id' key
        track_id = track.get("id")
        if not track_id:
            logger.debug(f"Skipping track without ID: {track}")
            return None

        # Get audio features from pre-fetched batch
        audio_features = audio_features_map.get(track_id, {})

        # Score track against mood (RELAXED for artist tracks)
        cohesion_score = self._calculate_artist_track_score(audio_features, target_features)

        # Ultra-relaxed threshold for artist tracks (0.2 vs 0.6 for RecoBeat)
        # Lower threshold to ensure enough tracks pass filtering
        if cohesion_score < 0.2:
            logger.info(
                f"Filtering low-cohesion artist track: {track.get('name')} "
                f"(cohesion: {cohesion_score:.2f} < 0.2 threshold)"
            )
            return None

        # Create recommendation using factory
        # Enhance track data with audio features and cohesion score
        enhanced_track = track.copy()
        enhanced_track["audio_features"] = audio_features

        return TrackRecommendationFactory.from_artist_top_track(
            track_data=enhanced_track,
            artist_id="",  # We don't have the artist_id here, but the method doesn't require it
            confidence_score=cohesion_score,
            reasoning=f"From mood-matched artist (cohesion: {cohesion_score:.2f})"
        )

    def _calculate_artist_track_score(
        self,
        audio_features: Any,
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for an artist track.

        Args:
            audio_features: Track's audio features
            target_features: Target mood features

        Returns:
            Confidence score
        """
        if target_features and audio_features:
            return self._calculate_track_cohesion(audio_features, target_features)
        else:
            return 0.75  # Higher default for artist tracks without features

    def _calculate_track_cohesion(
        self,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track's audio features match target mood features.

        Args:
            audio_features: Track's audio features
            target_features: Target mood features

        Returns:
            Cohesion score (0-1)
        """
        if not audio_features or not target_features:
            return 0.5

        scores = []

        # Define tolerance thresholds
        tolerance_thresholds = {
            "energy": 0.3,
            "valence": 0.3,
            "danceability": 0.3,
            "acousticness": 0.4,
            "instrumentalness": 0.25,
            "speechiness": 0.25,
            "tempo": 40.0,
            "loudness": 6.0,
            "liveness": 0.4,
            "popularity": 30
        }

        for feature_name, target_value in target_features.items():
            if feature_name not in audio_features:
                continue

            actual_value = audio_features[feature_name]
            tolerance = tolerance_thresholds.get(feature_name)

            if tolerance is None:
                continue

            # Convert target value to single number if it's a range
            if isinstance(target_value, list) and len(target_value) == 2:
                target_single = sum(target_value) / 2
            elif isinstance(target_value, (int, float)):
                target_single = float(target_value)
            else:
                continue

            # Calculate difference and score
            difference = abs(actual_value - target_single)
            match_score = max(0.0, 1.0 - (difference / tolerance))
            scores.append(match_score)

        # Return average match score
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5
