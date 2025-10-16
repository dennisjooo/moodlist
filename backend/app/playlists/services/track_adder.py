"""Track adder component for adding tracks to Spotify playlists."""

import asyncio
import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...agents.states.agent_state import AgentState

from ...agents.tools.spotify_service import SpotifyService

logger = structlog.get_logger(__name__)


class TrackAdder:
    """Handles adding recommended tracks to Spotify playlists."""

    def __init__(self, spotify_service: SpotifyService):
        """Initialize the track adder.

        Args:
            spotify_service: Service for Spotify API operations
        """
        self.spotify_service = spotify_service

    async def add_tracks_to_playlist(self, state: "AgentState", playlist_id: str):
        """Add recommended tracks to the Spotify playlist.

        Args:
            state: Current agent state
            playlist_id: Spotify playlist ID
        """
        try:
            if not state.recommendations:
                logger.warning("No recommendations to add to playlist")
                return

            # Extract and normalize Spotify URIs from recommendations
            track_uris = []
            for rec in state.recommendations:
                if rec.spotify_uri:
                    normalized_uri = self._normalize_spotify_uri(rec.spotify_uri)
                    if normalized_uri:
                        track_uris.append(normalized_uri)
                        logger.debug(f"Normalized URI: {rec.spotify_uri} -> {normalized_uri}")
                    else:
                        logger.warning(f"Could not normalize URI for track {rec.track_id}: {rec.spotify_uri}")
                elif rec.track_id:
                    # Try to use track_id as fallback
                    normalized_uri = self._normalize_spotify_uri(rec.track_id)
                    if normalized_uri:
                        track_uris.append(normalized_uri)
                        logger.debug(f"Using track_id as URI: {rec.track_id} -> {normalized_uri}")
                else:
                    logger.warning(f"No Spotify URI or track ID for recommendation")

            if not track_uris:
                logger.error("No valid Spotify URIs found in recommendations")
                return

            logger.info(f"Adding {len(track_uris)} tracks to playlist {playlist_id}")
            logger.debug(f"First 3 URIs: {track_uris[:3]}")

            # Split into chunks to respect API limits (100 tracks per request)
            chunk_size = 100
            for i in range(0, len(track_uris), chunk_size):
                chunk = track_uris[i:i + chunk_size]

                # Add tracks to playlist
                access_token = state.metadata.get("spotify_access_token")
                success = await self.spotify_service.add_tracks_to_playlist(
                    access_token=access_token,
                    playlist_id=playlist_id,
                    track_uris=chunk
                )

                if not success:
                    logger.error(f"Failed to add track chunk {i//chunk_size} to playlist")
                    continue

                # Add delay between chunks to respect rate limits
                await asyncio.sleep(0.1)

            logger.info(f"Successfully added tracks to playlist {playlist_id}")

        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {str(e)}", exc_info=True)
            # Don't fail the entire process for track addition errors
            state.metadata["track_addition_error"] = str(e)

    def _normalize_spotify_uri(self, uri_or_id: str) -> str:
        """Normalize track identifier to proper Spotify URI format.

        Args:
            uri_or_id: Track URI or ID

        Returns:
            Properly formatted Spotify URI
        """
        if not uri_or_id:
            return None

        # If already a proper URI, return as-is
        if uri_or_id.startswith('spotify:track:'):
            return uri_or_id

        # If it's a URI with different format, extract ID
        if 'spotify:' in uri_or_id:
            parts = uri_or_id.split(':')
            if len(parts) >= 3:
                return f"spotify:track:{parts[-1]}"

        # If it's just an ID, format it
        # Remove any URL prefixes if present
        track_id = uri_or_id.split('/')[-1].split('?')[0]
        return f"spotify:track:{track_id}"