"""User-mentioned track search handler."""

import structlog
from typing import List, Dict, Any

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
        self,
        user_mentioned_tracks: List[Dict[str, Any]],
        access_token: str
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

        found_tracks = []
        found_track_ids = []

        for track_info in user_mentioned_tracks:
            track_name = track_info.get("track_name")
            artist_name = track_info.get("artist_name")
            priority = track_info.get("priority", "medium")

            try:
                # Search Spotify for the track
                search_query = f"track:{track_name} artist:{artist_name}"
                search_results = await self.spotify_service.search_spotify_tracks(
                    access_token=access_token,
                    query=search_query,
                    limit=3
                )

                if search_results and len(search_results) > 0:
                    # Take the first result (best match)
                    track = search_results[0]
                    track_id = track.get("id")

                    if track_id:
                        found_tracks.append({
                            "id": track_id,
                            "name": track.get("name"),
                            "artist": track.get("artists", [{}])[0].get("name"),
                            "artist_id": track.get("artists", [{}])[0].get("id"),
                            "uri": track.get("uri"),
                            "popularity": track.get("popularity", 50),
                            "user_mentioned": True,
                            "priority": priority,
                            "anchor_type": "user",
                            "protected": True
                        })
                        found_track_ids.append(track_id)

                        logger.info(
                            f"✓ Found user-mentioned track: '{track.get('name')}' "
                            f"by {track.get('artists', [{}])[0].get('name')} (priority: {priority})"
                        )
                else:
                    logger.warning(f"Could not find track: '{track_name}' by {artist_name}")

            except Exception as e:
                logger.error(f"Error searching for track '{track_name}': {e}")

        logger.info(f"Found {len(found_tracks)}/{len(user_mentioned_tracks)} user-mentioned tracks")
        return found_track_ids, found_tracks

