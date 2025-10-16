"""Playlist repository for playlist-specific database operations."""

from typing import List, Optional

import structlog
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from app.models.playlist import Playlist
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class PlaylistRepository(BaseRepository[Playlist]):
    """Repository for playlist-specific database operations."""

    @property
    def model_class(self) -> type[Playlist]:
        """Return the Playlist model class."""
        return Playlist

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        load_relationships: Optional[List[str]] = None
    ) -> List[Playlist]:
        """Get playlists for a specific user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted playlists
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of user's playlists
        """
        try:
            query = select(Playlist).where(Playlist.user_id == user_id)

            # Exclude soft-deleted unless explicitly requested
            if not include_deleted:
                query = query.where(Playlist.deleted_at.is_(None))

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by creation date (newest first)
            query = query.order_by(desc(Playlist.created_at))

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Playlist, relationship)))

            result = await self.session.execute(query)
            playlists = result.scalars().all()

            self.logger.debug(
                "User playlists retrieved successfully",
                user_id=user_id,
                count=len(playlists),
                skip=skip,
                limit=limit
            )

            return list(playlists)

        except Exception as e:
            self.logger.error(
                "Database error retrieving user playlists",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_by_session_id(self, session_id: str, load_relationships: Optional[List[str]] = None) -> Optional[Playlist]:
        """Get playlist by workflow session ID.

        Args:
            session_id: Workflow session UUID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Playlist instance or None if not found
        """
        try:
            query = select(Playlist).where(Playlist.session_id == session_id)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Playlist, relationship)))

            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug("Playlist retrieved by session ID", session_id=session_id)
            else:
                self.logger.debug("Playlist not found for session ID", session_id=session_id)

            return playlist

        except Exception as e:
            self.logger.error(
                "Database error retrieving playlist by session ID",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def get_by_spotify_id(self, spotify_playlist_id: str, load_relationships: Optional[List[str]] = None) -> Optional[Playlist]:
        """Get playlist by Spotify playlist ID.

        Args:
            spotify_playlist_id: Spotify playlist ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Playlist instance or None if not found
        """
        try:
            query = select(Playlist).where(Playlist.spotify_playlist_id == spotify_playlist_id)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Playlist, relationship)))

            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug("Playlist retrieved by Spotify ID", spotify_playlist_id=spotify_playlist_id)
            else:
                self.logger.debug("Playlist not found for Spotify ID", spotify_playlist_id=spotify_playlist_id)

            return playlist

        except Exception as e:
            self.logger.error(
                "Database error retrieving playlist by Spotify ID",
                spotify_playlist_id=spotify_playlist_id,
                error=str(e)
            )
            raise

    async def get_recent_by_user(
        self,
        user_id: int,
        limit: int = 10,
        load_relationships: Optional[List[str]] = None
    ) -> List[Playlist]:
        """Get recent playlists for a user.

        Args:
            user_id: User ID
            limit: Maximum number of playlists to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of recent playlists
        """
        return await self.get_by_user_id(
            user_id=user_id,
            limit=limit,
            load_relationships=load_relationships
        )

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[Playlist]:
        """Get playlists by status.

        Args:
            status: Playlist status
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of playlists with the specified status
        """
        try:
            query = select(Playlist).where(
                and_(
                    Playlist.status == status,
                    Playlist.deleted_at.is_(None)
                )
            )

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by creation date (newest first)
            query = query.order_by(desc(Playlist.created_at))

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Playlist, relationship)))

            result = await self.session.execute(query)
            playlists = result.scalars().all()

            self.logger.debug(
                "Playlists retrieved by status",
                status=status,
                count=len(playlists),
                skip=skip,
                limit=limit
            )

            return list(playlists)

        except Exception as e:
            self.logger.error(
                "Database error retrieving playlists by status",
                status=status,
                error=str(e)
            )
            raise

    async def update_status(self, playlist_id: int, status: str, error_message: Optional[str] = None) -> Playlist:
        """Update playlist status.

        Args:
            playlist_id: Playlist ID
            status: New status
            error_message: Optional error message

        Returns:
            Updated playlist instance
        """
        update_data = {"status": status}
        if error_message is not None:
            update_data["error_message"] = error_message

        return await self.update(playlist_id, **update_data)

    async def soft_delete(self, playlist_id: int) -> bool:
        """Soft delete a playlist.

        Args:
            playlist_id: Playlist ID

        Returns:
            True if deleted, False if not found
        """
        try:
            from sqlalchemy import update
            from datetime import datetime, timezone

            query = (
                update(Playlist)
                .where(Playlist.id == playlist_id)
                .values(deleted_at=datetime.now(timezone.utc))
            )

            result = await self.session.execute(query)
            deleted = result.rowcount > 0

            if deleted:
                self.logger.info("Playlist soft deleted successfully", playlist_id=playlist_id)
            else:
                self.logger.debug("Playlist not found for soft deletion", playlist_id=playlist_id)

            return deleted

        except Exception as e:
            self.logger.error(
                "Database error soft deleting playlist",
                playlist_id=playlist_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def get_user_playlist_count(self, user_id: int, include_deleted: bool = False) -> int:
        """Get total playlist count for a user.

        Args:
            user_id: User ID
            include_deleted: Include soft-deleted playlists

        Returns:
            Number of playlists
        """
        try:
            query = select(func.count(Playlist.id)).where(Playlist.user_id == user_id)

            if not include_deleted:
                query = query.where(Playlist.deleted_at.is_(None))

            result = await self.session.execute(query)
            count = result.scalar()

            self.logger.debug(
                "User playlist count retrieved",
                user_id=user_id,
                count=count,
                include_deleted=include_deleted
            )

            return count or 0

        except Exception as e:
            self.logger.error(
                "Database error counting user playlists",
                user_id=user_id,
                error=str(e)
            )
            raise