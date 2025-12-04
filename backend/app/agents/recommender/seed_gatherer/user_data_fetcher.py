"""User data fetching and merging.

This module handles:
- Fetching user's top tracks
- Fetching user's top artists
- Merging user-mentioned tracks into seed pool
"""

import time

import structlog

from ...states.agent_state import AgentState
from ...tools.spotify_service import SpotifyService


logger = structlog.get_logger(__name__)


class UserDataFetcher:
    """Fetches and merges user's top tracks and artists."""

    def __init__(self, spotify_service: SpotifyService):
        """Initialize the user data fetcher.

        Args:
            spotify_service: Service for Spotify API operations
        """
        self.spotify_service = spotify_service

    async def fetch_top_tracks(
        self,
        state: AgentState,
        access_token: str,
        is_remix: bool,
        remix_tracks: list,
        notify_progress_callback,
    ) -> tuple[list, float | None]:
        """Fetch top tracks for seed selection.

        Args:
            state: Current agent state
            access_token: Spotify access token
            is_remix: Whether in remix mode
            remix_tracks: Remix tracks (if applicable)
            notify_progress_callback: Async callback for progress updates

        Returns:
            Tuple of (top_tracks, fetch_time). fetch_time is None for remix mode.
        """
        state.current_step = "gathering_seeds_fetching_top_tracks"
        await notify_progress_callback(state)

        if remix_tracks:
            logger.info(f"Using {len(remix_tracks)} remix tracks as seed source")
            # Optimization: Limit remix tracks to reduce enrichment overhead
            if len(remix_tracks) > 30:
                logger.info(f"Limiting remix tracks from {len(remix_tracks)} to 30 for processing")
                top_tracks = remix_tracks[:30]
            else:
                top_tracks = remix_tracks
            fetch_time = None
        else:
            # Optimization: Pass user_id to enable caching
            step_start = time.time()
            top_tracks = await self.spotify_service.get_user_top_tracks(
                access_token=access_token,
                limit=20,
                time_range="medium_term",
                user_id=state.user_id,
            )
            fetch_time = time.time() - step_start

        # Progress update after fetching tracks
        state.current_step = "gathering_seeds_tracks_fetched"
        await notify_progress_callback(state)

        return top_tracks, fetch_time

    def merge_user_mentioned_tracks(self, state: AgentState, top_tracks: list) -> list:
        """Merge user-mentioned tracks into top tracks for seed selection.

        Args:
            state: Current agent state
            top_tracks: Current top tracks list

        Returns:
            Merged track list with user-mentioned tracks at the beginning
        """
        user_mentioned_tracks_full = state.metadata.get("user_mentioned_tracks_full", [])
        if not user_mentioned_tracks_full:
            return top_tracks

        # Deduplicate by track ID
        existing_track_ids = {track["id"] for track in top_tracks if track.get("id")}
        new_user_tracks = [
            track for track in user_mentioned_tracks_full
            if track.get("id") and track["id"] not in existing_track_ids
        ]

        if new_user_tracks:
            # Add user-mentioned tracks to the beginning (higher priority)
            logger.info(f"Added {len(new_user_tracks)} user-mentioned tracks to seed pool")
            return new_user_tracks + top_tracks

        return top_tracks

    async def fetch_top_artists(
        self,
        state: AgentState,
        access_token: str,
        is_remix: bool,
        notify_progress_callback,
    ) -> list:
        """Fetch top artists and return the list.

        Args:
            state: Current agent state
            access_token: Spotify access token
            is_remix: Whether in remix mode
            notify_progress_callback: Async callback for progress updates

        Returns:
            List of top artists
        """
        state.current_step = "gathering_seeds_fetching_top_artists"
        await notify_progress_callback(state)

        # Optimization: Reduce top artist fetch for remixing
        top_artist_limit = 5 if is_remix else 15

        top_artists = await self.spotify_service.get_user_top_artists(
            access_token=access_token,
            limit=top_artist_limit,
            time_range="medium_term",
            user_id=state.user_id,
        )

        # Progress update after fetching artists
        state.current_step = "gathering_seeds_artists_fetched"
        await notify_progress_callback(state)

        return top_artists
