"""Spotify edit service for editing playlists saved to Spotify."""

import structlog
from typing import Optional, Dict, Any

from ...clients.spotify_client import SpotifyAPIClient
from ...core.exceptions import SpotifyAPIException

logger = structlog.get_logger(__name__)


class SpotifyEditService:
    """Handles direct edits to Spotify playlists."""

    def __init__(self):
        """Initialize the Spotify edit service."""
        self.spotify_client = SpotifyAPIClient()

    async def remove_track_from_spotify(
        self, playlist_id: str, track_uri: str, access_token: str
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
            await self.spotify_client.remove_tracks_from_playlist(
                access_token=access_token,
                playlist_id=playlist_id,
                track_uris=[track_uri],
            )
            logger.info(
                f"Removed track {track_uri} from Spotify playlist {playlist_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error removing track from Spotify: {str(e)}", exc_info=True)
            raise SpotifyAPIException(f"Failed to remove track from Spotify: {str(e)}")

    async def reorder_track_in_spotify(
        self, playlist_id: str, old_position: int, new_position: int, access_token: str
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
            # Spotify uses insert_before, so if moving down, add 1
            insert_before = (
                new_position if old_position > new_position else new_position + 1
            )

            await self.spotify_client.reorder_playlist_tracks(
                access_token=access_token,
                playlist_id=playlist_id,
                range_start=old_position,
                insert_before=insert_before,
                range_length=1,
            )
            logger.info(
                f"Reordered track from position {old_position} to {new_position} in Spotify"
            )
            return True
        except Exception as e:
            logger.error(f"Error reordering track in Spotify: {str(e)}", exc_info=True)
            raise SpotifyAPIException(f"Failed to reorder track in Spotify: {str(e)}")

    async def add_track_to_spotify(
        self,
        playlist_id: str,
        track_uri: str,
        access_token: str,
        position: Optional[int] = None,
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
            await self.spotify_client.add_tracks_to_playlist(
                access_token=access_token,
                playlist_id=playlist_id,
                track_uris=[track_uri],
                position=position,
            )
            logger.info(f"Added track {track_uri} to Spotify playlist {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding track to Spotify: {str(e)}", exc_info=True)
            raise SpotifyAPIException(f"Failed to add track to Spotify: {str(e)}")

    async def get_track_details(
        self, track_id: str, access_token: str
    ) -> Dict[str, Any]:
        """Get track details from Spotify.

        Args:
            track_id: Spotify track ID
            access_token: Spotify access token

        Returns:
            Track details dictionary
        """
        try:
            return await self.spotify_client.get_track(
                access_token=access_token, track_id=track_id
            )
        except Exception as e:
            logger.error(
                f"Error getting track details from Spotify: {str(e)}", exc_info=True
            )
            raise SpotifyAPIException(
                f"Failed to get track details from Spotify: {str(e)}"
            )
