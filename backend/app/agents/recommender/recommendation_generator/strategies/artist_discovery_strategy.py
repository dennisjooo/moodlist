"""Strategy for generating recommendations from mood-matched artists."""

import structlog
from typing import Any, Dict, List

from ....tools.reccobeat_service import RecoBeatService
from ....tools.spotify_service import SpotifyService
from ....states.agent_state import AgentState
from ....core.cache import cache_manager
from ...utils import TokenService, TrackRecommendationFactory
from ..audio_features import AudioFeaturesHandler
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
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)

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
        # Get mood-matched artists from state metadata
        mood_matched_artists = state.metadata.get("mood_matched_artists", [])

        if not mood_matched_artists:
            logger.info("No mood-matched artists available for recommendations")
            return []

        # Filter out artists that have failed recently
        filtered_artists = []
        skipped_failed_artists = 0

        for artist_id in mood_matched_artists:
            if await cache_manager.is_artist_failed(artist_id):
                logger.info(f"Filtering out previously failed artist {artist_id} from recommendation generation")
                skipped_failed_artists += 1
            else:
                filtered_artists.append(artist_id)

        if skipped_failed_artists > 0:
            logger.info(f"Filtered out {skipped_failed_artists} previously failed artists, "
                       f"processing {len(filtered_artists)} remaining artists")

        mood_matched_artists = filtered_artists

        if not mood_matched_artists:
            logger.info("No valid artists remaining after filtering failed ones")
            return []

        logger.info(f"Generating recommendations from {len(mood_matched_artists)} discovered artists")

        # Prepare parameters and refresh token
        access_token, target_features, tracks_per_artist = await self._prepare_artist_discovery_params(state)

        if not access_token:
            return []

        # Process all artists
        all_recommendations, successful_artists, failed_artists = await self._process_all_artists(
            mood_matched_artists, access_token, target_features, tracks_per_artist
        )

        # Handle error cases
        self._handle_artist_discovery_errors(successful_artists, failed_artists, len(mood_matched_artists))

        logger.info(
            f"Generated {len(all_recommendations)} recommendations from {successful_artists}/{min(len(mood_matched_artists), 20)} artists "
            f"({failed_artists} failed) - maximized diversity by spreading across more artists"
        )

        return [rec.dict() for rec in all_recommendations]

    async def _prepare_artist_discovery_params(self, state: AgentState) -> tuple[str, Dict[str, Any], int]:
        """Prepare parameters for artist discovery.

        Args:
            state: Current agent state

        Returns:
            Tuple of (access_token, target_features, tracks_per_artist)
        """
        # CRITICAL: Refresh Spotify token RIGHT BEFORE making API calls
        state = await TokenService.refresh_token_from_workflow(state)

        # Get target features for filtering
        target_features = state.metadata.get("target_features", {})

        # Get artist target (95% of total playlist target - DOMINANT source, 95:5 ratio)
        target_artist_recs = state.metadata.get("_temp_artist_target", 19)  # Default 95% of 20

        # Get access token for Spotify API (after refresh)
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.error("CRITICAL: No Spotify access token available for artist top tracks (even after refresh attempt)")
            return None, {}, 0

        logger.info(f"Using Spotify access token (length: {len(access_token)}, first 20 chars: {access_token[:20]}...)")

        # MAXIMIZE DIVERSITY: Use MORE artists with MORE tracks each to account for filtering
        artist_count = min(len(state.metadata.get("mood_matched_artists", [])), 20)
        tracks_per_artist = max(3, min(int((target_artist_recs * 2.5) // artist_count) + 2, 5))

        logger.info(
            f"MAXIMIZING DIVERSITY: Fetching {tracks_per_artist} tracks from up to {artist_count} artists "
            f"(aiming for ~{tracks_per_artist * artist_count} tracks before filtering) "
            f"to reach artist target of {target_artist_recs} tracks after filtering (95:5 ratio)"
        )

        return access_token, target_features, tracks_per_artist

    async def _process_all_artists(
        self,
        mood_matched_artists: List[str],
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int
    ) -> tuple[List[Any], int, int]:
        """Process all artists to get recommendations.

        Args:
            mood_matched_artists: List of artist IDs
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch per artist

        Returns:
            Tuple of (recommendations, successful_artists, failed_artists)
        """
        all_recommendations = []
        successful_artists = 0
        failed_artists = 0

        # Fetch tracks from each artist (use up to 20 artists for maximum coverage and variety)
        for idx, artist_id in enumerate(mood_matched_artists[:20]):
            try:
                artist_recommendations = await self._fetch_tracks_from_artist(
                    artist_id, idx, len(mood_matched_artists), access_token, target_features, tracks_per_artist
                )
                all_recommendations.extend(artist_recommendations)

                if artist_recommendations:  # Only count as successful if we got recommendations
                    successful_artists += 1
                else:
                    failed_artists += 1

            except Exception as e:
                logger.error(f"Error getting tracks for artist {artist_id} (artist {idx+1}/{min(len(mood_matched_artists), 20)}): {e}", exc_info=True)
                failed_artists += 1
                continue

        return all_recommendations, successful_artists, failed_artists

    async def _fetch_tracks_from_artist(
        self,
        artist_id: str,
        artist_index: int,
        total_artists: int,
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int
    ) -> List[Any]:
        """Fetch and process tracks from a single artist.

        Args:
            artist_id: Spotify artist ID
            artist_index: Index of this artist in the list
            total_artists: Total number of artists
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch

        Returns:
            List of TrackRecommendation objects from this artist
        """
        # Check if this artist has failed recently - skip if so
        if await cache_manager.is_artist_failed(artist_id):
            logger.info(
                f"Skipping previously failed artist {artist_id} (artist {artist_index+1}/{min(total_artists, 20)}) - "
                f"marked as failed, will retry after cache TTL expires"
            )
            return []

        logger.info(f"Fetching top tracks for artist {artist_index+1}/{min(total_artists, 20)}: {artist_id}")

        # Get top tracks from Spotify (more reliable than RecoBeat)
        artist_tracks = await self.spotify_service.get_artist_top_tracks(
            access_token=access_token,
            artist_id=artist_id,
            market="US"
        )

        if not artist_tracks:
            logger.warning(
                f"No tracks returned for artist {artist_id} (artist {artist_index+1}/{min(total_artists, 20)}) - "
                f"This may indicate a Spotify API authentication issue or invalid artist ID"
            )
            # Mark this artist as failed so we skip it next time
            await cache_manager.mark_artist_failed(artist_id)
            return []

        # If we got tracks, clear any previous failure mark (in case it was intermittent)
        await cache_manager.clear_failed_artist(artist_id)

        logger.info(
            f"Successfully got {len(artist_tracks)} tracks from artist {artist_id}, "
            f"will process top {tracks_per_artist} for recommendations"
        )

        # Process tracks from this artist
        return await self._process_artist_tracks(
            artist_tracks[:tracks_per_artist], artist_id, target_features
        )

    async def _process_artist_tracks(
        self,
        artist_tracks: List[Dict[str, Any]],
        artist_id: str,
        target_features: Dict[str, Any]
    ) -> List[Any]:
        """Process tracks from an artist into recommendations.

        Args:
            artist_tracks: List of track data from Spotify
            artist_id: Spotify artist ID
            target_features: Target mood features

        Returns:
            List of TrackRecommendation objects
        """
        # Batch fetch audio features for all tracks first
        track_data = []
        for track in artist_tracks:
            track_id = track.get("id")
            if track_id:
                track_data.append((track_id, None))
        
        audio_features_map = await self.audio_features_handler.get_batch_complete_audio_features(track_data)
        
        recommendations = []
        tracks_added = 0

        for track in artist_tracks:
            try:
                recommendation = await self._create_artist_track_recommendation(track, target_features, audio_features_map)
                if recommendation:
                    recommendations.append(recommendation)
                    tracks_added += 1

            except Exception as e:
                logger.warning(f"Failed to process artist track: {e}")
                continue

        # Log how many tracks were actually added from this artist
        logger.info(
            f"Added {tracks_added}/{len(artist_tracks)} tracks from artist {artist_id} "
            f"({len(artist_tracks) - tracks_added} filtered out)"
        )

        return recommendations

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

        # Very relaxed threshold for artist tracks (0.3 vs 0.6 for RecoBeat)
        if cohesion_score < 0.3:
            logger.info(
                f"Filtering low-cohesion artist track: {track.get('name')} "
                f"(cohesion: {cohesion_score:.2f} < 0.3 threshold)"
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

    def _handle_artist_discovery_errors(
        self,
        successful_artists: int,
        failed_artists: int,
        total_artists: int
    ) -> None:
        """Handle error cases for artist discovery.

        Args:
            successful_artists: Number of successful artists
            failed_artists: Number of failed artists
            total_artists: Total number of artists attempted
        """
        total_attempted = min(total_artists, 20)

        if failed_artists > total_attempted * 0.5:  # More than 50% failed
            logger.error(
                f"CRITICAL: Artist discovery failed for {failed_artists}/{total_attempted} artists. "
                f"This may indicate an expired Spotify access token or API issue. "
                f"Only {successful_artists} artists succeeded."
            )

            # If ALL artists failed, raise an error to prevent bad recommendations
            if successful_artists == 0:
                raise Exception(
                    f"Artist discovery completely failed - all {total_attempted} artists returned no tracks. "
                    "This is likely due to an expired or invalid Spotify access token. "
                    "The workflow cannot continue without valid artist tracks."
                )
