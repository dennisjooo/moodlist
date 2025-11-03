"""Playlist service for business logic related to playlist operations."""

from typing import List, Dict, Any, Optional

import structlog

from app.clients.spotify_client import SpotifyAPIClient
from app.repositories.playlist_repository import PlaylistRepository
from app.repositories.user_repository import UserRepository
from app.core.exceptions import NotFoundException, ValidationException
from app.core.constants import PlaylistStatus

logger = structlog.get_logger(__name__)


class PlaylistService:
    """Service for playlist business logic operations."""

    def __init__(
        self,
        spotify_client: SpotifyAPIClient,
        playlist_repository: PlaylistRepository,
        user_repository: UserRepository
    ):
        """Initialize the playlist service.

        Args:
            spotify_client: Spotify API client
            playlist_repository: Playlist repository
            user_repository: User repository
        """
        self.spotify_client = spotify_client
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
        self.logger = logger.bind(service="PlaylistService")

    async def create_playlist(
        self,
        user_id: int,
        name: str,
        description: str = "",
        public: bool = False,
        track_uris: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new playlist for a user.

        Args:
            user_id: User ID
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public
            track_uris: Optional list of track URIs to add

        Returns:
            Created playlist data

        Raises:
            NotFoundException: If user not found
            SpotifyAPIException: If Spotify API call fails
        """
        try:
            # Get user to ensure they exist and get Spotify ID
            user = await self.user_repository.get_by_id_or_fail(user_id)

            if not user.spotify_id:
                raise ValidationException("User does not have a Spotify ID")

            self.logger.info(
                "Creating playlist",
                user_id=user_id,
                spotify_user_id=user.spotify_id,
                playlist_name=name
            )

            # Create playlist on Spotify
            spotify_playlist = await self.spotify_client.create_playlist(
                access_token=user.access_token,
                user_id=user.spotify_id,
                name=name,
                description=description,
                public=public
            )

            # Save playlist to database
            db_playlist = await self.playlist_repository.create(
                user_id=user_id,
                session_id=None,  # Not part of a workflow session
                spotify_playlist_id=spotify_playlist["id"],
                name=name,
                description=description,
                status=PlaylistStatus.COMPLETED,
                track_count=len(track_uris) if track_uris else 0,
                metadata={
                    "spotify_uri": spotify_playlist.get("uri"),
                    "spotify_url": spotify_playlist.get("external_urls", {}).get("spotify"),
                    "public": public
                }
            )

            # Add tracks if provided
            if track_uris:
                await self.spotify_client.add_tracks_to_playlist(
                    access_token=user.access_token,
                    playlist_id=spotify_playlist["id"],
                    track_uris=track_uris
                )

            self.logger.info(
                "Successfully created playlist",
                playlist_id=db_playlist.id,
                spotify_playlist_id=spotify_playlist["id"]
            )

            return {
                "id": db_playlist.id,
                "spotify_id": spotify_playlist["id"],
                "name": name,
                "description": description,
                "track_count": len(track_uris) if track_uris else 0,
                "spotify_url": spotify_playlist.get("external_urls", {}).get("spotify"),
                "created_at": db_playlist.created_at.isoformat()
            }

        except Exception as e:
            self.logger.error(
                "Failed to create playlist",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_user_playlists(
        self,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Get playlists for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted playlists

        Returns:
            List of playlist data
        """
        try:
            playlists = await self.playlist_repository.get_by_user_id(
                user_id=user_id,
                skip=skip,
                limit=limit,
                include_deleted=include_deleted
            )

            return [
                {
                    "id": p.id,
                    "spotify_id": p.spotify_playlist_id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "track_count": p.track_count,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "spotify_url": p.metadata.get("spotify_url") if p.metadata else None
                }
                for p in playlists
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get user playlists",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_playlist_by_id(self, playlist_id: int, user_id: int) -> Dict[str, Any]:
        """Get a specific playlist by ID.

        Args:
            playlist_id: Playlist ID
            user_id: User ID (for ownership validation)

        Returns:
            Playlist data

        Raises:
            NotFoundException: If playlist not found or doesn't belong to user
        """
        try:
            playlist = await self.playlist_repository.get_by_id_for_user(playlist_id, user_id)

            if not playlist:
                raise NotFoundException("Playlist", str(playlist_id))

            return {
                "id": playlist.id,
                "session_id": playlist.session_id,
                "mood_prompt": playlist.mood_prompt,
                "status": playlist.status,
                "track_count": playlist.track_count,
                "duration_ms": playlist.duration_ms,
                "playlist_data": playlist.playlist_data,
                "recommendations_data": playlist.recommendations_data,
                "mood_analysis_data": playlist.mood_analysis_data,
                "spotify_playlist_id": playlist.spotify_playlist_id,
                "error_message": playlist.error_message,
                "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
                "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
            }

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to get playlist by ID",
                playlist_id=playlist_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def update_playlist_details(
        self,
        playlist_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update playlist details.

        Args:
            playlist_id: Playlist ID
            user_id: User ID (for ownership validation)
            name: New playlist name
            description: New playlist description

        Returns:
            Updated playlist data

        Raises:
            NotFoundException: If playlist not found or doesn't belong to user
        """
        try:
            # Get and validate playlist ownership
            playlist = await self.playlist_repository.get_by_id_or_fail(playlist_id)

            if playlist.user_id != user_id:
                raise NotFoundException("Playlist", str(playlist_id))

            # Prepare update data
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description

            if not update_data:
                # No updates provided, return current data
                return await self.get_playlist_by_id(playlist_id, user_id)

            # Update in database
            await self.playlist_repository.update(playlist_id, **update_data)

            self.logger.info(
                "Updated playlist details",
                playlist_id=playlist_id,
                user_id=user_id
            )

            return await self.get_playlist_by_id(playlist_id, user_id)

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to update playlist details",
                playlist_id=playlist_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def delete_playlist(self, playlist_id: int, user_id: int) -> bool:
        """Soft delete a playlist.

        Args:
            playlist_id: Playlist ID
            user_id: User ID (for ownership validation)

        Returns:
            True if deleted

        Raises:
            NotFoundException: If playlist not found or doesn't belong to user
        """
        try:
            # Get and validate playlist ownership
            playlist = await self.playlist_repository.get_by_id_or_fail(playlist_id)

            if playlist.user_id != user_id:
                raise NotFoundException("Playlist", str(playlist_id))

            # Soft delete
            await self.playlist_repository.soft_delete(playlist_id)

            self.logger.info(
                "Soft deleted playlist",
                playlist_id=playlist_id,
                user_id=user_id
            )

            return True

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to delete playlist",
                playlist_id=playlist_id,
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_playlist_count(self, user_id: int, include_deleted: bool = False) -> int:
        """Get playlist count for a user.

        Args:
            user_id: User ID
            include_deleted: Include soft-deleted playlists

        Returns:
            Number of playlists
        """
        try:
            return await self.playlist_repository.get_user_playlist_count(
                user_id=user_id,
                include_deleted=include_deleted
            )

        except Exception as e:
            self.logger.error(
                "Failed to get playlist count",
                user_id=user_id,
                error=str(e)
            )
            raise
