"""Shared pipeline for artist-based recommendation generation.

This module provides a common implementation for processing mood-matched artists
and generating recommendations from their top tracks. It eliminates code duplication
between artist_based.py and artist_discovery_strategy.py.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple
import structlog

from ....states.agent_state import AgentState, TrackRecommendation
from ....tools.spotify_service import SpotifyService
from ....tools.reccobeat_service import RecoBeatService
from ....core.cache import cache_manager
from .audio_features import AudioFeaturesHandler
from .token import TokenManager

logger = structlog.get_logger(__name__)


class ArtistRecommendationPipeline:
    """Common pipeline for artist-based recommendation generation.

    This class encapsulates the shared logic for:
    - Token refreshing
    - Parameter calculation
    - Artist iteration and track fetching
    - Audio feature enrichment
    - Error handling
    """

    def __init__(
        self,
        spotify_service: SpotifyService,
        reccobeat_service: RecoBeatService,
        use_failed_artist_caching: bool = False
    ):
        """Initialize the artist recommendation pipeline.

        Args:
            spotify_service: Service for Spotify API operations
            reccobeat_service: Service for RecoBeat API operations
            use_failed_artist_caching: Whether to cache and filter failed artists
        """
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.token_manager = TokenManager()
        self.use_failed_artist_caching = use_failed_artist_caching

    async def process_artists(
        self,
        state: AgentState,
        create_recommendation_fn: Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Dict[str, Any]]], Optional[TrackRecommendation]],
        calculate_score_fn: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], float]
    ) -> List[Dict[str, Any]]:
        """Process mood-matched artists and generate recommendations.

        Args:
            state: Current agent state
            create_recommendation_fn: Callback to create a recommendation from a track
            calculate_score_fn: Callback to calculate a score for a track

        Returns:
            List of recommendation dictionaries
        """
        # Get mood-matched artists from state metadata
        mood_matched_artists = state.metadata.get("mood_matched_artists", [])

        if not mood_matched_artists:
            logger.info("No mood-matched artists available for recommendations")
            return []

        # Filter failed artists if caching is enabled
        if self.use_failed_artist_caching:
            mood_matched_artists = await self._filter_failed_artists(mood_matched_artists)

        if not mood_matched_artists:
            logger.info("No valid artists remaining after filtering")
            return []

        logger.info(f"Generating recommendations from {len(mood_matched_artists)} discovered artists")

        # Prepare parameters and refresh token
        access_token, target_features, tracks_per_artist = await self._prepare_params(state)

        if not access_token:
            return []

        # Process all artists
        all_recommendations, successful_artists, failed_artists = await self._process_all_artists(
            mood_matched_artists,
            access_token,
            target_features,
            tracks_per_artist,
            create_recommendation_fn,
            calculate_score_fn
        )

        # Handle error cases
        self._handle_errors(successful_artists, failed_artists, len(mood_matched_artists))

        logger.info(
            f"Generated {len(all_recommendations)} recommendations from {successful_artists}/"
            f"{min(len(mood_matched_artists), 20)} artists ({failed_artists} failed)"
        )

        return [rec.dict() for rec in all_recommendations]

    async def _filter_failed_artists(self, artists: List[str]) -> List[str]:
        """Filter out artists that have failed recently (if caching enabled).

        Args:
            artists: List of artist IDs

        Returns:
            Filtered list of artist IDs
        """
        filtered_artists = []
        skipped_count = 0

        for artist_id in artists:
            if await cache_manager.is_artist_failed(artist_id):
                logger.debug(f"Filtering out previously failed artist {artist_id}")
                skipped_count += 1
            else:
                filtered_artists.append(artist_id)

        if skipped_count > 0:
            logger.info(
                f"Filtered out {skipped_count} previously failed artists, "
                f"processing {len(filtered_artists)} remaining artists"
            )

        return filtered_artists

    async def _prepare_params(self, state: AgentState) -> Tuple[Optional[str], Dict[str, Any], int]:
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

        # Get artist target
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
        tracks_per_artist: int,
        create_recommendation_fn: Callable,
        calculate_score_fn: Callable
    ) -> Tuple[List[TrackRecommendation], int, int]:
        """Process all artists to get recommendations in parallel.

        Args:
            mood_matched_artists: List of artist IDs
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch per artist
            create_recommendation_fn: Callback to create recommendations
            calculate_score_fn: Callback to calculate scores

        Returns:
            Tuple of (recommendations, successful_artists, failed_artists)
        """
        # Use up to 20 artists for maximum coverage
        artists_to_process = mood_matched_artists[:20]
        
        # Process artists in parallel with bounded concurrency (4-6 concurrent)
        semaphore = asyncio.Semaphore(5)
        
        async def process_artist_bounded(idx: int, artist_id: str) -> Tuple[List[TrackRecommendation], bool]:
            """Process a single artist with concurrency control."""
            async with semaphore:
                try:
                    artist_recommendations = await self._fetch_tracks_from_artist(
                        artist_id,
                        idx,
                        len(mood_matched_artists),
                        access_token,
                        target_features,
                        tracks_per_artist,
                        create_recommendation_fn,
                        calculate_score_fn
                    )
                    success = len(artist_recommendations) > 0
                    return artist_recommendations, success
                    
                except Exception as e:
                    logger.error(
                        f"Error getting tracks for artist {artist_id} "
                        f"(artist {idx+1}/{len(artists_to_process)}): {e}",
                        exc_info=True
                    )
                    return [], False
        
        # Create tasks for all artists
        tasks = [
            process_artist_bounded(idx, artist_id)
            for idx, artist_id in enumerate(artists_to_process)
        ]
        
        # Execute all tasks in parallel with bounded concurrency
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        all_recommendations = []
        successful_artists = 0
        failed_artists = 0
        
        for artist_recommendations, success in results:
            all_recommendations.extend(artist_recommendations)
            if success:
                successful_artists += 1
            else:
                failed_artists += 1

        return all_recommendations, successful_artists, failed_artists

    async def _fetch_tracks_from_artist(
        self,
        artist_id: str,
        artist_index: int,
        total_artists: int,
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int,
        create_recommendation_fn: Callable,
        calculate_score_fn: Callable
    ) -> List[TrackRecommendation]:
        """Fetch and process tracks from a single artist.

        Args:
            artist_id: Spotify artist ID
            artist_index: Index of this artist in the list
            total_artists: Total number of artists
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch
            create_recommendation_fn: Callback to create recommendations
            calculate_score_fn: Callback to calculate scores

        Returns:
            List of TrackRecommendation objects from this artist
        """
        # Check if this artist has failed recently (if caching enabled)
        if self.use_failed_artist_caching:
            if await cache_manager.is_artist_failed(artist_id):
                logger.debug(
                    f"Skipping previously failed artist {artist_id} "
                    f"(artist {artist_index+1}/{min(total_artists, 20)})"
                )
                return []

        logger.info(
            f"Fetching hybrid tracks for artist {artist_index+1}/{min(total_artists, 20)}: {artist_id}"
        )

        # Get diverse tracks using hybrid strategy (top tracks + album deep cuts)
        # For mood-based discovery, favor album diversity (30% top tracks, 70% album tracks)
        artist_tracks = await self.spotify_service.get_artist_hybrid_tracks(
            access_token=access_token,
            artist_id=artist_id,
            market="US",
            max_popularity=80,  # Exclude mega-hits (tracks > 80 popularity)
            min_popularity=20,  # Ensure minimum quality
            target_count=tracks_per_artist,
            top_tracks_ratio=0.3  # Discovery-focused: 30% top tracks, 70% album tracks
        )

        if not artist_tracks:
            logger.warning(
                f"No tracks returned for artist {artist_id} "
                f"(artist {artist_index+1}/{min(total_artists, 20)})"
            )
            # Mark this artist as failed (if caching enabled)
            if self.use_failed_artist_caching:
                await cache_manager.mark_artist_failed(artist_id)
            return []

        # Clear any previous failure mark (if caching enabled)
        if self.use_failed_artist_caching:
            await cache_manager.clear_failed_artist(artist_id)

        logger.info(
            f"Got {len(artist_tracks)} tracks from artist {artist_id}, "
            f"processing top {tracks_per_artist}"
        )

        # Process tracks from this artist
        return await self._process_artist_tracks(
            artist_tracks[:tracks_per_artist],
            artist_id,
            target_features,
            create_recommendation_fn,
            calculate_score_fn
        )

    async def _process_artist_tracks(
        self,
        artist_tracks: List[Dict[str, Any]],
        artist_id: str,
        target_features: Dict[str, Any],
        create_recommendation_fn: Callable,
        calculate_score_fn: Callable
    ) -> List[TrackRecommendation]:
        """Process tracks from an artist into recommendations.

        Args:
            artist_tracks: List of track data from Spotify
            artist_id: Spotify artist ID
            target_features: Target mood features
            create_recommendation_fn: Callback to create recommendations
            calculate_score_fn: Callback to calculate scores

        Returns:
            List of TrackRecommendation objects
        """
        # Batch fetch audio features for all tracks first
        track_data = []
        for track in artist_tracks:
            track_id = track.get("id")
            if track_id:
                track_data.append((track_id, None))

        audio_features_map = await self.audio_features_handler.get_batch_complete_audio_features(
            track_data
        )

        recommendations = []
        tracks_added = 0

        for track in artist_tracks:
            try:
                recommendation = await create_recommendation_fn(
                    track,
                    target_features,
                    audio_features_map,
                    calculate_score_fn
                )
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
