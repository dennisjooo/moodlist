"""Spotify edit service for editing playlists saved to Spotify."""

import json
import logging
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class SpotifyEditService:
    """Handles direct edits to Spotify playlists."""

    def __init__(self):
        """Initialize the Spotify edit service."""
        pass

    async def remove_track_from_spotify(
        self,
        playlist_id: str,
        track_uri: str,
        access_token: str
    ) -> bool:
        """Remove a track from a Spotify playlist.

        Args:
            playlist_id: Spotify playlist ID
            track_uri: Track URI to remove
            access_token: Spotify access token

        Returns:
            Whether the operation was successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "DELETE",
                    f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    content=json.dumps({"tracks": [{"uri": track_uri}]})
                )
                response.raise_for_status()
                logger.info(f"Removed track {track_uri} from Spotify playlist {playlist_id}")
                return True
        except Exception as e:
            logger.error(f"Error removing track from Spotify: {str(e)}", exc_info=True)
            raise

    async def reorder_track_in_spotify(
        self,
        playlist_id: str,
        old_position: int,
        new_position: int,
        access_token: str
    ) -> bool:
        """Reorder a track in a Spotify playlist.

        Args:
            playlist_id: Spotify playlist ID
            old_position: Current position of track
            new_position: New position for track
            access_token: Spotify access token

        Returns:
            Whether the operation was successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Spotify uses insert_before, so if moving down, add 1
                insert_before = new_position if old_position > new_position else new_position + 1
                
                response = await client.put(
                    f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "range_start": old_position,
                        "insert_before": insert_before,
                        "range_length": 1
                    }
                )
                response.raise_for_status()
                logger.info(f"Reordered track from position {old_position} to {new_position} in Spotify")
                return True
        except Exception as e:
            logger.error(f"Error reordering track in Spotify: {str(e)}", exc_info=True)
            raise

    async def add_track_to_spotify(
        self,
        playlist_id: str,
        track_uri: str,
        access_token: str,
        position: Optional[int] = None
    ) -> bool:
        """Add a track to a Spotify playlist.

        Args:
            playlist_id: Spotify playlist ID
            track_uri: Track URI to add
            access_token: Spotify access token
            position: Optional position to insert track

        Returns:
            Whether the operation was successful
        """
        try:
            async with httpx.AsyncClient() as client:
                json_data = {"uris": [track_uri]}
                if position is not None:
                    json_data["position"] = position

                response = await client.post(
                    f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=json_data
                )
                response.raise_for_status()
                logger.info(f"Added track {track_uri} to Spotify playlist {playlist_id}")
                return True
        except Exception as e:
            logger.error(f"Error adding track to Spotify: {str(e)}", exc_info=True)
            raise

    async def get_track_details(
        self,
        track_id: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Get track details from Spotify.

        Args:
            track_id: Spotify track ID
            access_token: Spotify access token

        Returns:
            Track details dictionary
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.spotify.com/v1/tracks/{track_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting track details from Spotify: {str(e)}", exc_info=True)
            raise

