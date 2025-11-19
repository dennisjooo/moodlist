"""User-mentioned track search handler."""

import asyncio
import structlog
from typing import List, Dict, Any, Optional, Tuple

logger = structlog.get_logger(__name__)


class UserTrackSearcher:
    """Handles searching for user-mentioned tracks."""

    def __init__(self, spotify_service):
        """Initialize the user track searcher.

        Args:
            spotify_service: Spotify service for API operations
        """
        self.spotify_service = spotify_service

    async def search_user_mentioned_tracks(
        self, user_mentioned_tracks: List[Dict[str, Any]], access_token: str
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        """Search for tracks explicitly mentioned by the user.

        Args:
            user_mentioned_tracks: List of track info from intent analysis
            access_token: Spotify access token

        Returns:
            Tuple of (found_track_ids, found_tracks_full)
        """
        if not user_mentioned_tracks:
            logger.info("No user-mentioned tracks to search for")
            return [], []

        logger.info(f"Searching for {len(user_mentioned_tracks)} user-mentioned tracks")

        semaphore = asyncio.Semaphore(6)

        tasks = [
            self._search_single_track(track_info, access_token, semaphore)
            for track_info in user_mentioned_tracks
        ]
        results = await asyncio.gather(*tasks)

        found_tracks = []
        found_track_ids = []
        for result in results:
            if result:
                track_id, track_entry = result
                if track_id:
                    found_track_ids.append(track_id)
                    found_tracks.append(track_entry)

        logger.info(
            f"Found {len(found_tracks)}/{len(user_mentioned_tracks)} user-mentioned tracks"
        )
        return found_track_ids, found_tracks

    async def _search_single_track(
        self,
        track_info: Dict[str, Any],
        access_token: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Search a single user-mentioned track with bounded concurrency.

        Args:
            track_info: Track information from intent analysis
            access_token: Spotify access token
            semaphore: Concurrency control semaphore

        Returns:
            Tuple of (track_id, track_entry) if found, None otherwise
        """
        track_name = track_info.get("track_name")
        artist_name = track_info.get("artist_name")
        priority = track_info.get("priority", "medium")

        async with semaphore:
            try:
                search_query = f"track:{track_name} artist:{artist_name}"
                search_results = await self.spotify_service.search_spotify_tracks(
                    access_token=access_token, query=search_query, limit=3
                )

                if search_results:
                    track = search_results[0]
                    track_id = track.get("id")

                    if track_id:
                        track_entry = {
                            "id": track_id,
                            "name": track.get("name"),
                            "artist": track.get("artists", [{}])[0].get("name"),
                            "artist_id": track.get("artists", [{}])[0].get("id"),
                            "uri": track.get("uri"),
                            "popularity": track.get("popularity", 50),
                            "user_mentioned": True,
                            "priority": priority,
                            "anchor_type": "user",
                            "protected": True,
                        }
                        logger.info(
                            f"✓ Found user-mentioned track: '{track.get('name')}' "
                            f"by {track.get('artists', [{}])[0].get('name')} (priority: {priority})"
                        )
                        return track_id, track_entry

                logger.warning(f"Could not find track: '{track_name}' by {artist_name}")
                return None

            except Exception as e:
                logger.error(f"Error searching for track '{track_name}': {e}")
                return None
