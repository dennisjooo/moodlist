"""Playlist repository for playlist-specific database operations."""

from typing import List, Optional, Dict, Iterable, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

import structlog
from sqlalchemy import select, and_, asc, desc, func, or_, String, literal, cast
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB

from app.models.playlist import Playlist
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import InternalServerError, ValidationException

logger = structlog.get_logger(__name__)


def safe_json_get(json_field: Optional[dict], key: str, default: Any = None) -> Any:
    """Safely get value from JSON field that might be None.
    
    Args:
        json_field: JSON field which might be None
        key: Key to retrieve
        default: Default value if field is None or key doesn't exist
        
    Returns:
        Value from JSON field or default
    """
    return json_field.get(key, default) if json_field else default


@dataclass
class PlaylistSessionSnapshot:
    """Lightweight projection of playlist/session data for quick lookups."""

    status: str
    mood_prompt: Optional[str]
    mood_analysis_data: Optional[Dict[str, Any]]
    spotify_playlist_id: Optional[str]
    playlist_data: Optional[Dict[str, Any]]
    recommendations_data: Optional[List[Dict[str, Any]]]
    recommendation_count: int
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class PlaylistRepository(BaseRepository[Playlist]):
    """Repository for playlist-specific database operations."""

    @property
    def model_class(self) -> type[Playlist]:
        """Return the Playlist model class."""
        return Playlist

    def _build_user_playlist_query(
        self,
        user_id: int,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        load_relationships: Optional[Iterable[str]] = None,
        search_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ):
        """Construct the common playlist query used by the user fetch helpers."""

        query = select(Playlist).where(Playlist.user_id == user_id)

        if not include_deleted:
            query = query.where(Playlist.deleted_at.is_(None))

        if status:
            query = query.where(Playlist.status == status)

        if search_query:
            search_term = f"%{search_query.lower()}%"
            playlist_name = func.coalesce(Playlist.playlist_data["name"].as_string(), "")
            primary_emotion = func.coalesce(Playlist.mood_analysis_data["primary_emotion"].as_string(), "")
            energy_level = func.coalesce(Playlist.mood_analysis_data["energy_level"].as_string(), "")
            recommendations_data = func.coalesce(func.cast(Playlist.recommendations_data, String), "")
            query = query.where(
                or_(
                    func.lower(Playlist.mood_prompt).like(search_term),
                    func.lower(playlist_name).like(search_term),
                    func.lower(primary_emotion).like(search_term),
                    func.lower(energy_level).like(search_term),
                    func.lower(Playlist.status).like(search_term),
                    func.lower(recommendations_data).like(search_term),
                )
            )

        if skip:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)

        # Sorting configuration
        sort_column = Playlist.created_at
        if sort_by == "name":
            sort_column = func.lower(
                func.coalesce(Playlist.playlist_data["name"].as_string(), Playlist.mood_prompt)
            )
        elif sort_by == "track_count":
            sort_column = Playlist.track_count

        order_func = desc if sort_order.lower() == "desc" else asc

        query = query.order_by(order_func(sort_column), desc(Playlist.created_at))

        if load_relationships:
            for relationship in load_relationships:
                query = query.options(selectinload(getattr(Playlist, relationship)))

        return query

    async def _execute_playlist_query(
        self,
        query,
        *,
        success_event: str,
        error_event: str,
        log_context: Optional[Dict[str, object]] = None,
    ) -> List[Playlist]:
        """Execute the playlist query and provide consistent logging."""

        log_context = log_context or {}

        try:
            result = await self.session.execute(query)
            playlists = list(result.scalars().all())
            self.logger.debug(success_event, count=len(playlists), **log_context)
            return playlists
        except Exception as exc:
            self.logger.error(error_event, error=str(exc), **log_context)
            raise

    async def get_by_user_id_with_filters(
        self,
        user_id: int,
        status: Optional[str] = None,  # Deprecated: use exclude_statuses instead
        exclude_statuses: Optional[List[str]] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        load_relationships: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[Playlist]:
        """Get playlists for a specific user with optional status filtering.

        Args:
            user_id: User ID
            status: Optional status filter (deprecated, use exclude_statuses)
            exclude_statuses: Optional list of statuses to exclude
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted playlists
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of user's playlists
        """
        query = self._build_user_playlist_query(
            user_id,
            status=status,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            load_relationships=load_relationships,
            search_query=search_query,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Add exclude statuses filter if provided (case insensitive)
        if exclude_statuses:
            # Validate all statuses are strings to prevent AttributeError
            for status_item in exclude_statuses:
                if not isinstance(status_item, str):
                    raise ValidationException(
                        f"Status must be a string, got {type(status_item).__name__}"
                    )
            query = query.where(func.lower(Playlist.status).not_in([status.lower() for status in exclude_statuses]))

        return await self._execute_playlist_query(
            query,
            success_event="User playlists retrieved with filters",
            error_event="Database error retrieving user playlists with filters",
            log_context={
                "user_id": user_id,
                "status": status,
                "exclude_statuses": exclude_statuses,
                "skip": skip,
                "limit": limit,
                "search_query": search_query,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )

    async def get_by_user_id_with_filters_and_count(
        self,
        user_id: int,
        status: Optional[str] = None,  # Deprecated: use exclude_statuses instead
        exclude_statuses: Optional[List[str]] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        search_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Tuple[List[Playlist], int]:
        """Get playlists for a specific user with count in a single optimized query.
        
        This method is more efficient than calling get_by_user_id_with_filters and
        count_user_playlists_with_filters separately as it performs both operations
        in a single database round-trip.

        Args:
            user_id: User ID
            status: Optional status filter (deprecated, use exclude_statuses)
            exclude_statuses: Optional list of statuses to exclude
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted playlists
            search_query: Optional search query string
            sort_by: Sort field (created_at, name, track_count)
            sort_order: Sort order (asc, desc)

        Returns:
            Tuple of (list of playlists, total count)
        """
        try:
            # Build the base WHERE clause
            where_clauses = [Playlist.user_id == user_id]
            
            if not include_deleted:
                where_clauses.append(Playlist.deleted_at.is_(None))
            
            if status:
                where_clauses.append(Playlist.status == status)
            elif exclude_statuses:
                # Validate all statuses are strings
                for status_item in exclude_statuses:
                    if not isinstance(status_item, str):
                        from app.core.exceptions import ValidationException
                        raise ValidationException(
                            f"Status must be a string, got {type(status_item).__name__}"
                        )
                where_clauses.append(
                    func.lower(Playlist.status).not_in([s.lower() for s in exclude_statuses])
                )
            
            # Add search conditions if provided
            if search_query:
                search_term = f"%{search_query.lower()}%"
                playlist_name = func.coalesce(Playlist.playlist_data["name"].as_string(), "")
                primary_emotion = func.coalesce(Playlist.mood_analysis_data["primary_emotion"].as_string(), "")
                energy_level = func.coalesce(Playlist.mood_analysis_data["energy_level"].as_string(), "")
                recommendations_data = func.coalesce(func.cast(Playlist.recommendations_data, String), "")
                
                where_clauses.append(
                    or_(
                        func.lower(Playlist.mood_prompt).like(search_term),
                        func.lower(playlist_name).like(search_term),
                        func.lower(primary_emotion).like(search_term),
                        func.lower(energy_level).like(search_term),
                        func.lower(Playlist.status).like(search_term),
                        func.lower(recommendations_data).like(search_term),
                    )
                )
            
            # First, get the total count with a simple count query
            count_query = select(func.count(Playlist.id)).where(and_(*where_clauses))
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # If total_count is 0, return early
            if total_count == 0:
                self.logger.debug(
                    "No playlists found for user with filters",
                    user_id=user_id,
                    search_query=search_query
                )
                return ([], 0)
            
            # Build the main query for playlists
            query = select(Playlist).where(and_(*where_clauses))
            
            # Apply sorting
            sort_column = Playlist.created_at
            if sort_by == "name":
                sort_column = func.lower(
                    func.coalesce(Playlist.playlist_data["name"].as_string(), Playlist.mood_prompt)
                )
            elif sort_by == "track_count":
                sort_column = Playlist.track_count
            
            order_func = desc if sort_order.lower() == "desc" else asc
            query = query.order_by(order_func(sort_column), desc(Playlist.created_at))
            
            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)
            
            # Execute query
            result = await self.session.execute(query)
            playlists = list(result.scalars().all())
            
            self.logger.debug(
                "User playlists retrieved with count (optimized)",
                user_id=user_id,
                count=len(playlists),
                total=total_count,
                skip=skip,
                limit=limit,
                search_query=search_query,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            
            return (playlists, total_count)
            
        except Exception as exc:
            self.logger.error(
                "Database error retrieving user playlists with count",
                user_id=user_id,
                error=str(exc),
                search_query=search_query,
            )
            raise

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
        query = self._build_user_playlist_query(
            user_id,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            load_relationships=load_relationships,
        )

        return await self._execute_playlist_query(
            query,
            success_event="User playlists retrieved successfully",
            error_event="Database error retrieving user playlists",
            log_context={
                "user_id": user_id,
                "skip": skip,
                "limit": limit,
            },
        )

    async def get_by_session_id_for_update(self, session_id: str) -> Optional[Playlist]:
        """Get playlist by session ID for update operations (no user check needed for internal operations).

        Args:
            session_id: Session ID

        Returns:
            Playlist instance or None if not found
        """
        try:
            query = select(Playlist).where(Playlist.session_id == session_id)
            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug("Playlist retrieved by session ID for update", session_id=session_id)
            else:
                self.logger.debug("Playlist not found by session ID for update", session_id=session_id)

            return playlist

        except Exception as e:
            self.logger.error(
                "Database error retrieving playlist by session ID for update",
                session_id=session_id,
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

    async def get_by_session_id_for_user(self, session_id: str, user_id: int, include_deleted: bool = False) -> Optional[Playlist]:
        """Get playlist by session ID with user ownership check.

        Args:
            session_id: Session ID
            user_id: User ID for ownership validation
            include_deleted: Include soft-deleted playlists

        Returns:
            Playlist instance or None if not found or not owned by user
        """
        try:
            query = select(Playlist).where(
                Playlist.session_id == session_id,
                Playlist.user_id == user_id
            )

            if not include_deleted:
                query = query.where(Playlist.deleted_at.is_(None))

            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug("Playlist retrieved by session ID for user", session_id=session_id, user_id=user_id)
            else:
                self.logger.debug("Playlist not found by session ID for user", session_id=session_id, user_id=user_id)

            return playlist

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving playlist by session ID for user",
                session_id=session_id,
                user_id=user_id,
                error=str(e)
            )
            raise InternalServerError("Failed to retrieve playlist")

    async def get_by_id_for_user(self, playlist_id: int, user_id: int, include_deleted: bool = False) -> Optional[Playlist]:
        """Get playlist by ID with user ownership check.

        Args:
            playlist_id: Playlist ID
            user_id: User ID for ownership validation
            include_deleted: Include soft-deleted playlists

        Returns:
            Playlist instance or None if not found or not owned by user
        """
        try:
            query = select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id
            )

            if not include_deleted:
                query = query.where(Playlist.deleted_at.is_(None))

            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug("Playlist retrieved for user", playlist_id=playlist_id, user_id=user_id)
            else:
                self.logger.debug("Playlist not found for user", playlist_id=playlist_id, user_id=user_id)

            return playlist

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving playlist for user",
                playlist_id=playlist_id,
                user_id=user_id,
                error=str(e)
            )
            raise InternalServerError("Failed to retrieve playlist")

    async def get_user_playlist_stats(self, user_id: int) -> Dict[str, int]:
        """Get comprehensive playlist statistics for a user with a single query.

        Args:
            user_id: User ID

        Returns:
            Dictionary with total_playlists, playlists saved to Spotify, and total_tracks
        """
        try:
            stmt = (
                select(
                    func.count(Playlist.id).label("total_playlists"),
                    func.count(Playlist.spotify_playlist_id).label("saved_playlists"),
                    func.coalesce(func.sum(Playlist.track_count), 0).label("total_tracks"),
                )
                .where(
                    Playlist.user_id == user_id,
                    Playlist.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            row = result.one()

            stats = {
                "total_playlists": row.total_playlists or 0,
                "saved_playlists": row.saved_playlists or 0,
                "total_tracks": row.total_tracks or 0,
            }

            self.logger.debug("User playlist stats retrieved", user_id=user_id, **stats)
            return stats

        except Exception as e:
            self.logger.error(
                "Database error retrieving user playlist stats",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_session_status_snapshot(self, session_id: str) -> Optional[PlaylistSessionSnapshot]:
        """Return lightweight playlist data needed for status polling.

        Args:
            session_id: Workflow session ID
        """
        try:
            recommendation_count_expr = func.coalesce(
                func.jsonb_array_length(cast(Playlist.recommendations_data, JSONB)), 0
            ).label("recommendation_count")

            stmt = (
                select(
                    Playlist.status,
                    Playlist.mood_prompt,
                    Playlist.mood_analysis_data,
                    Playlist.spotify_playlist_id,
                    Playlist.error_message,
                    Playlist.created_at,
                    Playlist.updated_at,
                    recommendation_count_expr,
                )
                .where(
                    Playlist.session_id == session_id,
                    Playlist.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            row = result.one_or_none()
            if not row:
                return None

            return PlaylistSessionSnapshot(
                status=row.status,
                mood_prompt=row.mood_prompt,
                mood_analysis_data=row.mood_analysis_data,
                spotify_playlist_id=row.spotify_playlist_id,
                playlist_data=None,  # defer heavy JSON for status polling
                recommendations_data=None,
                recommendation_count=row.recommendation_count or 0,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

        except Exception as e:
            self.logger.error(
                "Database error retrieving session status snapshot",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_session_results_snapshot(self, session_id: str) -> Optional[PlaylistSessionSnapshot]:
        """Return playlist data required to build final workflow results."""
        try:
            stmt = (
                select(
                    Playlist.status,
                    Playlist.mood_prompt,
                    Playlist.mood_analysis_data,
                    Playlist.spotify_playlist_id,
                    Playlist.playlist_data,
                    Playlist.recommendations_data,
                    Playlist.error_message,
                    Playlist.created_at,
                    Playlist.updated_at,
                )
                .where(
                    Playlist.session_id == session_id,
                    Playlist.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            row = result.one_or_none()
            if not row:
                return None

            recommendations = row.recommendations_data or []

            return PlaylistSessionSnapshot(
                status=row.status,
                mood_prompt=row.mood_prompt,
                mood_analysis_data=row.mood_analysis_data,
                spotify_playlist_id=row.spotify_playlist_id,
                playlist_data=row.playlist_data,
                recommendations_data=recommendations,
                recommendation_count=len(recommendations),
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

        except Exception as e:
            self.logger.error(
                "Database error retrieving session results snapshot",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_public_playlist_stats(self) -> Dict[str, int]:
        """Get public platform statistics.

        Returns:
            Dictionary with total_users, total_playlists, and completed_playlists
        """
        try:
            from app.models.user import User

            # Total active users
            users_query = select(func.count(User.id)).where(User.is_active.is_(True))
            users_result = await self.session.execute(users_query)
            total_users = users_result.scalar() or 0

            # Total playlists (including soft-deleted for historical stats)
            playlists_query = select(func.count(Playlist.id))
            playlists_result = await self.session.execute(playlists_query)
            total_playlists = playlists_result.scalar() or 0

            # Completed playlists
            completed_query = select(func.count(Playlist.id)).where(Playlist.status == "completed")
            completed_result = await self.session.execute(completed_query)
            completed_playlists = completed_result.scalar() or 0

            stats = {
                "total_users": total_users,
                "total_playlists": total_playlists,
                "completed_playlists": completed_playlists
            }

            self.logger.debug("Public playlist stats retrieved", **stats)
            return stats

        except Exception as e:
            self.logger.error(
                "Database error retrieving public playlist stats",
                error=str(e)
            )
            raise

    async def update_playlist_spotify_info(
        self,
        session_id: str,
        spotify_playlist_id: str,
        playlist_name: str,
        spotify_url: str,
        spotify_uri: Optional[str] = None
    ) -> bool:
        """Update playlist with Spotify information after saving to Spotify.

        Args:
            session_id: Playlist session ID
            spotify_playlist_id: Spotify playlist ID
            playlist_name: Playlist name
            spotify_url: Spotify playlist URL
            spotify_uri: Spotify playlist URI (optional)

        Returns:
            True if updated successfully, False if playlist not found
        """
        try:
            from datetime import datetime, timezone
            from app.core.constants import PlaylistStatus

            # Build playlist data
            playlist_data = {
                "name": playlist_name,
                "spotify_url": spotify_url
            }
            if spotify_uri:
                playlist_data["spotify_uri"] = spotify_uri

            # Update the playlist
            update_data = {
                "spotify_playlist_id": spotify_playlist_id,
                "status": PlaylistStatus.COMPLETED,
                "playlist_data": playlist_data,
                "updated_at": datetime.now(timezone.utc)
            }

            # Use a raw update query since we need to update by session_id
            from sqlalchemy import update
            query = (
                update(Playlist)
                .where(Playlist.session_id == session_id)
                .values(**update_data)
            )

            result = await self.session.execute(query)
            updated = result.rowcount > 0

            if updated:
                self.logger.info(
                    "Playlist updated with Spotify info",
                    session_id=session_id,
                    spotify_playlist_id=spotify_playlist_id
                )
            else:
                self.logger.warning(
                    "Playlist not found for Spotify info update",
                    session_id=session_id
                )

            return updated

        except Exception as e:
            self.logger.error(
                "Database error updating playlist Spotify info",
                session_id=session_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def count_user_playlists_with_filters(
        self,
        user_id: int,
        status: Optional[str] = None,  # Deprecated: use exclude_statuses instead
        exclude_statuses: Optional[List[str]] = None,
        include_deleted: bool = False,
        search_query: Optional[str] = None,
    ) -> int:
        """Count playlists for a user with optional status filtering.

        Args:
            user_id: User ID
            status: Optional status filter (deprecated, use exclude_statuses)
            exclude_statuses: Optional list of statuses to exclude
            include_deleted: Include soft-deleted playlists

        Returns:
            Number of playlists matching criteria
        """
        try:
            query = select(func.count(Playlist.id)).where(Playlist.user_id == user_id)

            # Exclude soft-deleted unless explicitly requested
            if not include_deleted:
                query = query.where(Playlist.deleted_at.is_(None))

            # Add status filter if provided (legacy support)
            if status:
                query = query.where(Playlist.status == status)
            elif exclude_statuses:
                # Exclude specified statuses (case insensitive)
                query = query.where(func.lower(Playlist.status).not_in([status.lower() for status in exclude_statuses]))
            else:
                # Exclude cancelled playlists by default unless specifically filtering for them
                query = query.where(Playlist.status != "cancelled")

            if search_query:
                search_term = f"%{search_query.lower()}%"
                playlist_name = func.coalesce(Playlist.playlist_data["name"].as_string(), "")
                primary_emotion = func.coalesce(Playlist.mood_analysis_data["primary_emotion"].as_string(), "")
                energy_level = func.coalesce(Playlist.mood_analysis_data["energy_level"].as_string(), "")
                recommendations_data = func.coalesce(func.cast(Playlist.recommendations_data, String), "")
                query = query.where(
                    or_(
                        func.lower(Playlist.mood_prompt).like(search_term),
                        func.lower(playlist_name).like(search_term),
                        func.lower(primary_emotion).like(search_term),
                        func.lower(energy_level).like(search_term),
                        func.lower(Playlist.status).like(search_term),
                        func.lower(recommendations_data).like(search_term),
                    )
                )

            result = await self.session.execute(query)
            count = result.scalar() or 0

            self.logger.debug(
                "User playlists counted with filters",
                user_id=user_id,
                status=status,
                count=count,
                include_deleted=include_deleted,
                search_query=search_query,
            )

            return count

        except Exception as e:
            self.logger.error(
                "Database error counting user playlists with filters",
                user_id=user_id,
                status=status,
                error=str(e)
            )
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

    async def count_user_playlists_created_today(self, user_id: int) -> int:
        """Count playlists created by user today (UTC).
        
        Args:
            user_id: User ID
            
        Returns:
            Number of playlists created today
        """
        try:
            # Get start of today in UTC
            now_utc = datetime.now(timezone.utc)
            start_of_today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            
            query = select(func.count(Playlist.id)).where(
                and_(
                    Playlist.user_id == user_id,
                    Playlist.created_at >= start_of_today,
                    Playlist.deleted_at.is_(None),
                    Playlist.status != "cancelled"
                )
            )
            
            result = await self.session.execute(query)
            count = result.scalar() or 0
            
            self.logger.debug(
                "User playlists created today counted",
                user_id=user_id,
                count=count,
                start_of_today=start_of_today.isoformat()
            )
            
            return count
            
        except Exception as e:
            self.logger.error(
                "Database error counting user playlists created today",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_by_session_id_and_user(
        self,
        session_id: str,
        user_id: int,
        load_relationships: Optional[List[str]] = None
    ) -> Optional[Playlist]:
        """Get playlist by session ID and user ID.

        Args:
            session_id: Workflow session ID
            user_id: User ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Playlist instance or None if not found
        """
        try:
            query = select(Playlist).where(
                and_(
                    Playlist.session_id == session_id,
                    Playlist.user_id == user_id
                )
            )

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Playlist, relationship)))

            result = await self.session.execute(query)
            playlist = result.scalar_one_or_none()

            if playlist:
                self.logger.debug(
                    "Playlist retrieved by session and user ID",
                    session_id=session_id,
                    user_id=user_id
                )
            else:
                self.logger.debug(
                    "Playlist not found for session and user ID",
                    session_id=session_id,
                    user_id=user_id
                )

            return playlist

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving playlist by session and user ID",
                session_id=session_id,
                user_id=user_id,
                error=str(e)
            )
            raise InternalServerError("Failed to retrieve playlist")

    async def create_playlist_for_session(
        self,
        user_id: int,
        session_id: str,
        mood_prompt: str,
        status: str,
        commit: bool = True
    ) -> Playlist:
        """Create a new playlist for a workflow session.

        Args:
            user_id: User ID
            session_id: Workflow session ID
            mood_prompt: User's mood description
            status: Initial playlist status
            commit: Whether to commit the transaction

        Returns:
            Created playlist instance
        """
        try:
            playlist = Playlist(
                user_id=user_id,
                session_id=session_id,
                mood_prompt=mood_prompt,
                status=status
            )

            self.session.add(playlist)

            if commit:
                await self.session.commit()
                await self.session.refresh(playlist)
            else:
                await self.session.flush()

            self.logger.info(
                "Playlist created for session",
                playlist_id=getattr(playlist, "id", None),
                session_id=session_id,
                user_id=user_id
            )

            return playlist

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error creating playlist for session",
                session_id=session_id,
                user_id=user_id,
                error=str(e)
            )
            await self.session.rollback()
            raise InternalServerError("Failed to create playlist")

    async def update_status(
        self,
        playlist_id: int,
        status: str,
        error_message: Optional[str] = None,
        commit: bool = True
    ) -> Playlist:
        """Update playlist status.

        Args:
            playlist_id: Playlist ID
            status: New status
            error_message: Error message if any (optional)
            commit: Whether to commit the transaction

        Returns:
            Updated playlist instance
        """
        try:
            playlist = await self.get_by_id_or_fail(playlist_id)

            playlist.status = status
            if error_message is not None:
                playlist.error_message = error_message

            if commit:
                await self.session.commit()
                await self.session.refresh(playlist)
            else:
                await self.session.flush()

            self.logger.info(
                "Playlist status updated",
                playlist_id=playlist_id,
                status=status
            )

            return playlist

        except Exception as e:
            self.logger.error(
                "Database error updating playlist status",
                playlist_id=playlist_id,
                status=status,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def update_status_by_session(
        self,
        session_id: str,
        status: str,
        error_message: Optional[str] = None,
        commit: bool = True
    ) -> Optional[Playlist]:
        """Update playlist status by session ID.

        Args:
            session_id: Workflow session ID
            status: New status
            error_message: Error message if any (optional)
            commit: Whether to commit the transaction

        Returns:
            Updated playlist instance or None if not found
        """
        try:
            playlist = await self.get_by_session_id(session_id)

            if not playlist:
                self.logger.warning("Playlist not found for status update", session_id=session_id)
                return None

            playlist.status = status
            if error_message is not None:
                playlist.error_message = error_message

            if commit:
                await self.session.commit()
                await self.session.refresh(playlist)
            else:
                await self.session.flush()

            self.logger.info(
                "Playlist status updated by session",
                session_id=session_id,
                status=status
            )

            return playlist

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error updating playlist status by session",
                session_id=session_id,
                status=status,
                error=str(e)
            )
            await self.session.rollback()
            raise InternalServerError("Failed to update playlist status")

    async def update_recommendations_data(
        self,
        playlist_id: int,
        recommendations_data: List[Dict],
        commit: bool = True
    ) -> Playlist:
        """Update playlist recommendations data.

        Args:
            playlist_id: Playlist ID
            recommendations_data: List of recommendations
            commit: Whether to commit the transaction

        Returns:
            Updated playlist instance
        """
        try:
            playlist = await self.get_by_id_or_fail(playlist_id)

            playlist.recommendations_data = recommendations_data

            if commit:
                await self.session.commit()
                await self.session.refresh(playlist)
            else:
                await self.session.flush()

            self.logger.info(
                "Playlist recommendations updated",
                playlist_id=playlist_id,
                recommendation_count=len(recommendations_data)
            )

            return playlist

        except Exception as e:
            self.logger.error(
                "Database error updating playlist recommendations",
                playlist_id=playlist_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def get_user_recent_playlists(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent playlists for a user with mood and metadata.

        Args:
            user_id: User ID
            limit: Number of recent playlists to fetch

        Returns:
            List of recent playlist data dictionaries
        """
        try:
            query = (
                select(
                    Playlist.id,
                    Playlist.mood_prompt,
                    Playlist.status,
                    Playlist.track_count,
                    Playlist.created_at,
                    Playlist.playlist_data,
                    Playlist.mood_analysis_data,
                )
                .where(
                    and_(
                        Playlist.user_id == user_id,
                        Playlist.deleted_at.is_(None)
                    )
                )
                .order_by(desc(Playlist.created_at))
                .limit(limit)
            )

            result = await self.session.execute(query)
            playlists = result.all()

            recent_data = []
            for (
                playlist_id,
                mood_prompt,
                status,
                track_count,
                created_at,
                playlist_data,
                mood_analysis_data,
            ) in playlists:
                playlist_info = {
                    "id": playlist_id,
                    "mood_prompt": mood_prompt,
                    "status": status,
                    "track_count": track_count,
                    "created_at": created_at.isoformat() if created_at else None,
                    "name": safe_json_get(playlist_data, "name"),
                    "spotify_url": safe_json_get(playlist_data, "spotify_url")
                }
                
                # Extract primary emotion if available
                playlist_info["primary_emotion"] = safe_json_get(mood_analysis_data, "primary_emotion")
                playlist_info["energy_level"] = safe_json_get(mood_analysis_data, "energy_level")
                
                recent_data.append(playlist_info)

            self.logger.debug("Recent playlists retrieved", user_id=user_id, count=len(recent_data))
            return recent_data

        except Exception as e:
            self.logger.error(
                "Database error retrieving recent playlists",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_user_dashboard_analytics(self, user_id: int) -> Dict:
        """Get comprehensive dashboard analytics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with mood distribution, audio insights, and status breakdown
        """
        try:
            filters = [
                Playlist.user_id == user_id,
                Playlist.deleted_at.is_(None),
            ]

            # Status breakdown using GROUP BY
            status_stmt = (
                select(Playlist.status, func.count(Playlist.id))
                .where(*filters)
                .group_by(Playlist.status)
            )
            status_rows = await self.session.execute(status_stmt)
            status_counts = {"pending": 0, "completed": 0, "failed": 0}
            for status, count in status_rows:
                if status in status_counts:
                    status_counts[status] = count or 0

            # Mood distribution
            emotion_expr = func.coalesce(
                cast(Playlist.mood_analysis_data["primary_emotion"], String),
                literal("Unknown"),
            ).label("emotion")
            mood_stmt = (
                select(emotion_expr, func.count(Playlist.id).label("count"))
                .where(*filters)
                .group_by(emotion_expr)
                .order_by(func.count(Playlist.id).desc())
            )
            mood_rows = await self.session.execute(mood_stmt)
            mood_distribution = [
                {"emotion": emotion or "Unknown", "count": count or 0}
                for emotion, count in mood_rows
            ][:5]

            # Energy distribution and audio feature averages
            energy_stmt = (
                select(
                    cast(Playlist.mood_analysis_data["energy_level"], String),
                    cast(Playlist.mood_analysis_data["target_features"], JSONB),
                )
                .where(*filters)
            )
            energy_rows = await self.session.execute(energy_stmt)

            energy_counts = {"high": 0, "medium": 0, "low": 0}
            avg_energy: List[float] = []
            avg_valence: List[float] = []
            avg_danceability: List[float] = []

            for energy_level, target_features in energy_rows:
                if energy_level:
                    normalized = energy_level.lower()
                    if "high" in normalized or "intense" in normalized:
                        energy_counts["high"] += 1
                    elif "low" in normalized or "calm" in normalized or "mellow" in normalized:
                        energy_counts["low"] += 1
                    else:
                        energy_counts["medium"] += 1

                if isinstance(target_features, dict):
                    energy_range = target_features.get("energy")
                    if isinstance(energy_range, list) and len(energy_range) == 2:
                        avg_energy.append(sum(energy_range) / 2)

                    valence_range = target_features.get("valence")
                    if isinstance(valence_range, list) and len(valence_range) == 2:
                        avg_valence.append(sum(valence_range) / 2)

                    dance_range = target_features.get("danceability")
                    if isinstance(dance_range, list) and len(dance_range) == 2:
                        avg_danceability.append(sum(dance_range) / 2)

            audio_insights = {
                "avg_energy": sum(avg_energy) / len(avg_energy) if avg_energy else 0,
                "avg_valence": sum(avg_valence) / len(avg_valence) if avg_valence else 0,
                "avg_danceability": sum(avg_danceability) / len(avg_danceability) if avg_danceability else 0,
                "energy_distribution": energy_counts,
            }

            analytics = {
                "mood_distribution": mood_distribution,
                "audio_insights": audio_insights,
                "status_breakdown": status_counts,
            }

            self.logger.debug("Dashboard analytics retrieved", user_id=user_id)
            return analytics

        except Exception as e:
            self.logger.error(
                "Database error retrieving dashboard analytics",
                user_id=user_id,
                error=str(e)
            )
            raise
