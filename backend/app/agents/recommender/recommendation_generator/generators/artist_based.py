"""Artist-based recommendation generator."""

import structlog
from typing import Any, Dict, List, Optional

from ....states.agent_state import AgentState, TrackRecommendation
from ....tools.spotify_service import SpotifyService
from ....tools.reccobeat_service import RecoBeatService
from ..handlers.scoring import ScoringEngine
from ..handlers.artist_pipeline import ArtistRecommendationPipeline

logger = structlog.get_logger(__name__)


class ArtistBasedGenerator:
    """Generates recommendations from discovered artists."""

    def __init__(
        self, spotify_service: SpotifyService, reccobeat_service: RecoBeatService
    ):
        """Initialize the artist-based generator.

        Args:
            spotify_service: Service for Spotify API operations
            reccobeat_service: Service for RecoBeat API operations
        """
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service
        self.scoring_engine = ScoringEngine()

        # Use shared pipeline (without failed artist caching)
        self.pipeline = ArtistRecommendationPipeline(
            spotify_service=spotify_service,
            reccobeat_service=reccobeat_service,
            use_failed_artist_caching=False,
        )

    async def generate_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from mood-matched artists.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from discovered artists
        """
        # Pass through progress callback if available (from parent agent)
        if hasattr(self, "_progress_callback"):
            self.pipeline._progress_callback = self._progress_callback

        # Use shared pipeline with our recommendation creation logic
        return await self.pipeline.process_artists(
            state=state,
            create_recommendation_fn=self._create_recommendation_wrapper,
            calculate_score_fn=self._calculate_track_score,
        )

    async def _create_recommendation_wrapper(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        audio_features_map: Dict[str, Dict[str, Any]],
        calculate_score_fn: callable,
    ) -> Optional[TrackRecommendation]:
        """Wrapper to adapt _create_recommendation to pipeline signature.

        Args:
            track: Track data from Spotify
            target_features: Target mood features
            audio_features_map: Pre-fetched audio features
            calculate_score_fn: Function to calculate score

        Returns:
            TrackRecommendation object or None if filtered out
        """
        return await self._create_recommendation(
            track, target_features, audio_features_map
        )

    async def _create_recommendation(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        audio_features_map: Dict[str, Dict[str, Any]],
    ) -> Optional[TrackRecommendation]:
        """Create a recommendation from an artist track.

        Args:
            track: Track data from Spotify
            target_features: Target mood features
            audio_features_map: Pre-fetched audio features for all tracks

        Returns:
            TrackRecommendation object or None if filtered out
        """
        track_id = track.get("id")
        if not track_id:
            return None

        # Get audio features from pre-fetched batch
        audio_features = audio_features_map.get(track_id, {})

        # Score track against mood (relaxed threshold for artist tracks)
        cohesion_score = self._calculate_track_score(audio_features, target_features)

        # Ultra-relaxed threshold for artist tracks (0.2 vs 0.6 for RecoBeat)
        # Lower threshold to ensure enough tracks pass filtering
        if cohesion_score < 0.2:
            logger.info(
                f"Filtering low-cohesion artist track: {track.get('name')} "
                f"(cohesion: {cohesion_score:.2f} < 0.2 threshold)"
            )
            return None

        # Extract artist names from Spotify format
        artist_names = [
            artist.get("name", "Unknown") for artist in track.get("artists", [])
        ]
        spotify_uri = track.get("spotify_uri") or track.get("uri")

        return TrackRecommendation(
            track_id=track_id,
            track_name=track.get("name", "Unknown Track"),
            artists=artist_names if artist_names else ["Unknown Artist"],
            spotify_uri=spotify_uri,
            confidence_score=cohesion_score,
            audio_features=audio_features,
            reasoning=f"From mood-matched artist (cohesion: {cohesion_score:.2f})",
            source="artist_discovery",
        )

    def _calculate_track_score(
        self, audio_features: Optional[Dict[str, Any]], target_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for an artist track.

        Args:
            audio_features: Track audio features
            target_features: Target mood features

        Returns:
            Confidence score
        """
        if target_features and audio_features:
            return self.scoring_engine.calculate_track_cohesion(
                audio_features, target_features
            )
        else:
            return 0.75  # Higher default for artist tracks without features
