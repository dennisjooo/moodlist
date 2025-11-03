"""Service for syncing playlist data from Spotify."""

from typing import Dict, Any, List
import structlog

from app.clients.spotify_client import SpotifyAPIClient
from app.repositories.playlist_repository import PlaylistRepository
from app.core.exceptions import NotFoundException, SpotifyAPIException

logger = structlog.get_logger(__name__)


class PlaylistSyncService:
    """Service for syncing playlist data from Spotify to local database."""

    def __init__(
        self,
        spotify_client: SpotifyAPIClient,
        playlist_repository: PlaylistRepository
    ):
        """Store dependencies for orchestrating Spotify sync operations.

        Args:
            spotify_client: Client used for invoking Spotify Web API calls.
            playlist_repository: Repository that persists playlist state locally.
        """
        self.spotify_client = spotify_client
        self.playlist_repository = playlist_repository
        self.logger = logger.bind(service="PlaylistSyncService")

    async def sync_from_spotify(
        self,
        session_id: str,
        access_token: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Sync playlist tracks from Spotify to local database.

        Args:
            session_id: Playlist session ID
            access_token: Spotify access token
            user_id: User ID for validation

        Returns:
            Sync results including updated playlist data

        Raises:
            NotFoundException: If playlist not found
            SpotifyAPIException: If Spotify API calls fail
        """
        self.logger.info("Starting playlist sync from Spotify", session_id=session_id)

        # Get playlist from database
        playlist = await self.playlist_repository.get_by_session_id_for_update(session_id)
        
        if not playlist:
            raise NotFoundException("Playlist", session_id)

        # Verify ownership
        if playlist.user_id != user_id:
            raise NotFoundException("Playlist", session_id)

        # Check if playlist has been saved to Spotify
        if not playlist.spotify_playlist_id:
            self.logger.warning(
                "Playlist not saved to Spotify yet",
                session_id=session_id
            )
            return {
                "session_id": session_id,
                "synced": False,
                "message": "Playlist has not been saved to Spotify yet"
            }

        spotify_playlist_id = playlist.spotify_playlist_id

        try:
            # Fetch all tracks from Spotify playlist (handle pagination)
            spotify_tracks = await self._fetch_all_playlist_tracks(
                access_token,
                spotify_playlist_id
            )

            self.logger.info(
                "Fetched tracks from Spotify",
                session_id=session_id,
                track_count=len(spotify_tracks)
            )

            # Get current local recommendations
            current_recommendations = playlist.recommendations_data or []

            # Build updated recommendations list based on Spotify order
            updated_recommendations = self._build_updated_recommendations(
                spotify_tracks,
                current_recommendations
            )

            # Prepare update data
            update_data = {
                "recommendations_data": updated_recommendations,
                "track_count": len(updated_recommendations)  # Update the track_count column
            }
            
            # Also update playlist_data if it exists
            if playlist.playlist_data:
                updated_playlist_data = playlist.playlist_data.copy()
                updated_playlist_data["track_count"] = len(updated_recommendations)
                update_data["playlist_data"] = updated_playlist_data

            # Update playlist in database using repository update method
            await self.playlist_repository.update(playlist.id, **update_data)

            self.logger.info(
                "Successfully synced playlist from Spotify",
                session_id=session_id,
                old_count=len(current_recommendations),
                new_count=len(updated_recommendations)
            )

            return {
                "session_id": session_id,
                "synced": True,
                "changes": {
                    "tracks_before": len(current_recommendations),
                    "tracks_after": len(updated_recommendations),
                    "tracks_added": max(0, len(updated_recommendations) - len(current_recommendations)),
                    "tracks_removed": max(0, len(current_recommendations) - len(updated_recommendations))
                },
                "recommendations": updated_recommendations,
                "playlist_data": playlist.playlist_data
            }

        except SpotifyAPIException as e:
            self.logger.error(
                "Failed to sync from Spotify",
                session_id=session_id,
                error=str(e)
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during sync",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            raise SpotifyAPIException(f"Failed to sync playlist: {str(e)}")

    async def _fetch_all_playlist_tracks(
        self,
        access_token: str,
        playlist_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch all tracks from a Spotify playlist, handling pagination.

        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID

        Returns:
            List of all tracks in the playlist
        """
        all_tracks = []
        offset = 0
        limit = 100

        while True:
            response = await self.spotify_client.get_playlist_tracks(
                access_token,
                playlist_id,
                limit=limit,
                offset=offset
            )

            items = response.get("items", [])
            if not items:
                break

            all_tracks.extend(items)

            # Check if there are more tracks
            if len(items) < limit or response.get("next") is None:
                break

            offset += limit

        return all_tracks

    def _build_updated_recommendations(
        self,
        spotify_tracks: List[Dict[str, Any]],
        current_recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build updated recommendations list based on Spotify track order.

        Args:
            spotify_tracks: Tracks from Spotify API
            current_recommendations: Current local recommendations

        Returns:
            Updated recommendations list
        """
        # Create a lookup map of existing recommendations by track URI/ID
        recommendations_map = {}
        for rec in current_recommendations:
            # Try multiple keys for matching
            track_id = rec.get("track_id")
            spotify_uri = rec.get("spotify_uri")
            
            if track_id:
                recommendations_map[track_id] = rec
            if spotify_uri:
                recommendations_map[spotify_uri] = rec
                # Also store by just the ID part
                if spotify_uri.startswith("spotify:track:"):
                    track_id_from_uri = spotify_uri.split(":")[-1]
                    recommendations_map[track_id_from_uri] = rec

        updated_recommendations = []

        for spotify_item in spotify_tracks:
            track = spotify_item.get("track")
            if not track:
                continue

            track_id = track.get("id")
            track_uri = track.get("uri")

            # Try to find existing recommendation data
            existing_rec = None
            if track_uri and track_uri in recommendations_map:
                existing_rec = recommendations_map[track_uri]
            elif track_id and track_id in recommendations_map:
                existing_rec = recommendations_map[track_id]
            elif track_uri and track_uri.startswith("spotify:track:"):
                track_id_from_uri = track_uri.split(":")[-1]
                existing_rec = recommendations_map.get(track_id_from_uri)

            # Build recommendation entry
            if existing_rec:
                # Use existing data but ensure URIs are up to date
                recommendation = {
                    **existing_rec,
                    "track_id": track_id,
                    "spotify_uri": track_uri,
                }
            else:
                # New track added on Spotify - create minimal entry
                artists = [artist.get("name") for artist in track.get("artists", [])]
                recommendation = {
                    "track_id": track_id,
                    "track_name": track.get("name"),
                    "artists": artists,
                    "spotify_uri": track_uri,
                    "confidence_score": 0.8,  # Default confidence for manually added tracks
                    "reasoning": "Track synced from Spotify",
                    "source": "spotify_sync"
                }

            updated_recommendations.append(recommendation)

        return updated_recommendations
