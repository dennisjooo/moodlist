"""Artist-based recommendation generator."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional

from ...states.agent_state import AgentState, TrackRecommendation
from ...tools.spotify_service import SpotifyService
from ...tools.reccobeat_service import RecoBeatService
from .audio_features import AudioFeaturesHandler
from .scoring_engine import ScoringEngine
from .token_manager import TokenManager

logger = structlog.get_logger(__name__)


class ArtistBasedGenerator:
    """Generates recommendations from discovered artists."""

    def __init__(self, spotify_service: SpotifyService, reccobeat_service: RecoBeatService):
        """Initialize the artist-based generator.

        Args:
            spotify_service: Service for Spotify API operations
            reccobeat_service: Service for RecoBeat API operations
        """
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.scoring_engine = ScoringEngine()
        self.token_manager = TokenManager()

    async def generate_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from mood-matched artists.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from discovered artists
        """
        # Get mood-matched artists from state metadata
        mood_matched_artists = state.metadata.get("mood_matched_artists", [])

        if not mood_matched_artists:
            logger.info("No mood-matched artists available for recommendations")
            return []

        logger.info(f"Generating recommendations from {len(mood_matched_artists)} discovered artists")

        # Prepare parameters and refresh token
        access_token, target_features, tracks_per_artist = await self._prepare_params(state)

        if not access_token:
            return []

        # Process all artists
        all_recommendations, successful_artists, failed_artists = await self._process_all_artists(
            mood_matched_artists, access_token, target_features, tracks_per_artist
        )

        # Handle error cases
        self._handle_errors(successful_artists, failed_artists, len(mood_matched_artists))

        logger.info(
            f"Generated {len(all_recommendations)} recommendations from {successful_artists}/"
            f"{min(len(mood_matched_artists), 20)} artists ({failed_artists} failed)"
        )

        return [rec.dict() for rec in all_recommendations]

    async def _prepare_params(self, state: AgentState) -> tuple[str, Dict[str, Any], int]:
        """Prepare parameters for artist discovery.

        Args:
            state: Current agent state

        Returns:
            Tuple of (access_token, target_features, tracks_per_artist)
        """
        # Refresh Spotify token before making API calls
        state = await self.token_manager.refresh_token_from_workflow(state)

        # Get target features for filtering
        target_features = state.metadata.get("target_features", {})

        # Get artist target (40-55% of total playlist target depending on user mentions)
        target_artist_recs = state.metadata.get("_temp_artist_target", 11)

        # Get access token for Spotify API (after refresh)
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.error("No Spotify access token available for artist top tracks")
            return None, {}, 0

        # Maximize diversity: Use more artists with more tracks to account for filtering
        artist_count = min(len(state.metadata.get("mood_matched_artists", [])), 20)
        tracks_per_artist = max(3, min(int((target_artist_recs * 2.5) // artist_count) + 2, 5))

        logger.info(
            f"Fetching {tracks_per_artist} tracks from up to {artist_count} artists "
            f"(target: {target_artist_recs} tracks after filtering)"
        )

        return access_token, target_features, tracks_per_artist

    async def _process_all_artists(
        self,
        mood_matched_artists: List[str],
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int
    ) -> tuple[List[TrackRecommendation], int, int]:
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

        # Fetch tracks from each artist (use up to 20 artists for maximum coverage)
        for idx, artist_id in enumerate(mood_matched_artists[:20]):
            try:
                artist_recommendations = await self._fetch_tracks_from_artist(
                    artist_id, idx, len(mood_matched_artists), access_token, 
                    target_features, tracks_per_artist
                )
                all_recommendations.extend(artist_recommendations)

                if artist_recommendations:
                    successful_artists += 1
                else:
                    failed_artists += 1

                # Small delay between artists
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(
                    f"Error getting tracks for artist {artist_id} "
                    f"(artist {idx+1}/{min(len(mood_matched_artists), 20)}): {e}", 
                    exc_info=True
                )
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
    ) -> List[TrackRecommendation]:
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
        logger.info(f"Fetching top tracks for artist {artist_index+1}/{min(total_artists, 20)}: {artist_id}")

        # Get top tracks from Spotify
        artist_tracks = await self.spotify_service.get_artist_top_tracks(
            access_token=access_token,
            artist_id=artist_id,
            market="US"
        )

        if not artist_tracks:
            logger.warning(
                f"No tracks returned for artist {artist_id} "
                f"(artist {artist_index+1}/{min(total_artists, 20)})"
            )
            return []

        logger.info(
            f"Got {len(artist_tracks)} tracks from artist {artist_id}, "
            f"processing top {tracks_per_artist}"
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
    ) -> List[TrackRecommendation]:
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
                recommendation = await self._create_recommendation(track, target_features, audio_features_map)
                if recommendation:
                    recommendations.append(recommendation)
                    tracks_added += 1

            except Exception as e:
                logger.warning(f"Failed to process artist track: {e}")
                continue

        logger.info(
            f"Added {tracks_added}/{len(artist_tracks)} tracks from artist {artist_id} "
            f"({len(artist_tracks) - tracks_added} filtered out)"
        )

        return recommendations

    async def _create_recommendation(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        audio_features_map: Dict[str, Dict[str, Any]]
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

        # Very relaxed threshold for artist tracks (0.3 vs 0.6 for RecoBeat)
        if cohesion_score < 0.3:
            logger.info(
                f"Filtering low-cohesion artist track: {track.get('name')} "
                f"(cohesion: {cohesion_score:.2f} < 0.3 threshold)"
            )
            return None

        # Extract artist names from Spotify format
        artist_names = [artist.get("name", "Unknown") for artist in track.get("artists", [])]
        spotify_uri = track.get("spotify_uri") or track.get("uri")

        return TrackRecommendation(
            track_id=track_id,
            track_name=track.get("name", "Unknown Track"),
            artists=artist_names if artist_names else ["Unknown Artist"],
            spotify_uri=spotify_uri,
            confidence_score=cohesion_score,
            audio_features=audio_features,
            reasoning=f"From mood-matched artist (cohesion: {cohesion_score:.2f})",
            source="artist_discovery"
        )

    def _calculate_track_score(
        self,
        audio_features: Optional[Dict[str, Any]],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for an artist track.

        Args:
            audio_features: Track audio features
            target_features: Target mood features

        Returns:
            Confidence score
        """
        if target_features and audio_features:
            return self.scoring_engine.calculate_track_cohesion(audio_features, target_features)
        else:
            return 0.75  # Higher default for artist tracks without features

    def _handle_errors(
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

        if failed_artists > total_attempted * 0.5:
            logger.error(
                f"CRITICAL: Artist discovery failed for {failed_artists}/{total_attempted} artists. "
                f"Only {successful_artists} artists succeeded."
            )

            # If ALL artists failed, raise an error
            if successful_artists == 0:
                raise Exception(
                    f"Artist discovery completely failed - all {total_attempted} artists returned no tracks. "
                    "This is likely due to an expired or invalid Spotify access token."
                )

