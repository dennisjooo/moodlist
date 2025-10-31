"""Session repository for session-specific database operations."""

from typing import List, Optional
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, desc, delete, and_, func
from sqlalchemy.orm import selectinload

from app.models.session import Session
from app.models.user import User
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class SessionRepository(BaseRepository[Session]):
    """Repository for session-specific database operations."""

    @property
    def model_class(self) -> type[Session]:
        """Return the Session model class."""
        return Session

    async def get_by_token(self, session_token: str, load_relationships: Optional[List[str]] = None) -> Optional[Session]:
        """Get session by session token.

        Args:
            session_token: Session token
            load_relationships: List of relationship names to eagerly load

        Returns:
            Session instance or None if not found
        """
        try:
            query = select(Session).where(Session.session_token == session_token)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Session, relationship)))

            result = await self.session.execute(query)
            session = result.scalar_one_or_none()

            if session:
                self.logger.debug("Session retrieved by token", session_token=session_token[:8] + "...")
            else:
                self.logger.debug("Session not found for token", session_token=session_token[:8] + "...")

            return session

        except Exception as e:
            self.logger.error(
                "Database error retrieving session by token",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            raise

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[Session]:
        """Get all sessions for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of user's sessions
        """
        try:
            query = select(Session).where(Session.user_id == user_id)

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by last activity (most recent first)
            query = query.order_by(desc(Session.last_activity))

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Session, relationship)))

            result = await self.session.execute(query)
            sessions = result.scalars().all()

            self.logger.debug(
                "User sessions retrieved successfully",
                user_id=user_id,
                count=len(sessions),
                skip=skip,
                limit=limit
            )

            return list(sessions)

        except Exception as e:
            self.logger.error(
                "Database error retrieving user sessions",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_active_sessions(
        self,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[Session]:
        """Get active (non-expired) sessions.

        Args:
            user_id: Optional user ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of active sessions
        """
        try:
            now = datetime.now(timezone.utc)
            query = select(Session).where(Session.expires_at > now)

            if user_id:
                query = query.where(Session.user_id == user_id)

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by last activity (most recent first)
            query = query.order_by(desc(Session.last_activity))

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Session, relationship)))

            result = await self.session.execute(query)
            sessions = result.scalars().all()

            self.logger.debug(
                "Active sessions retrieved successfully",
                user_id=user_id,
                count=len(sessions),
                skip=skip,
                limit=limit
            )

            return list(sessions)

        except Exception as e:
            self.logger.error(
                "Database error retrieving active sessions",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_expired_sessions(
        self,
        before_timestamp: Optional[datetime] = None,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[Session]:
        """Get expired sessions.

        Args:
            before_timestamp: Optional timestamp to get sessions expired before this time
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of expired sessions
        """
        try:
            now = datetime.now(timezone.utc)
            query = select(Session).where(Session.expires_at <= now)

            if before_timestamp:
                query = query.where(Session.expires_at <= before_timestamp)

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by expiration date (oldest first for cleanup)
            query = query.order_by(Session.expires_at)

            result = await self.session.execute(query)
            sessions = result.scalars().all()

            self.logger.debug(
                "Expired sessions retrieved successfully",
                before_timestamp=before_timestamp.isoformat() if before_timestamp else None,
                count=len(sessions),
                skip=skip,
                limit=limit
            )

            return list(sessions)

        except Exception as e:
            self.logger.error(
                "Database error retrieving expired sessions",
                before_timestamp=before_timestamp.isoformat() if before_timestamp else None,
                error=str(e)
            )
            raise

    async def update_last_activity(self, session_id: int) -> Session:
        """Update session's last activity timestamp.

        Args:
            session_id: Session ID

        Returns:
            Updated session instance
        """
        now = datetime.now(timezone.utc)
        return await self.update(session_id, last_activity=now)

    async def extend_session(self, session_id: int, new_expires_at: datetime) -> Session:
        """Extend session expiration time.

        Args:
            session_id: Session ID
            new_expires_at: New expiration timestamp

        Returns:
            Updated session instance
        """
        return await self.update(session_id, expires_at=new_expires_at)

    async def delete_expired_sessions(self, before_timestamp: Optional[datetime] = None) -> int:
        """Delete expired sessions.

        Args:
            before_timestamp: Optional timestamp to delete sessions expired before this time

        Returns:
            Number of deleted sessions
        """
        try:
            now = datetime.now(timezone.utc)
            query = delete(Session).where(Session.expires_at <= now)

            if before_timestamp:
                query = query.where(Session.expires_at <= before_timestamp)

            result = await self.session.execute(query)
            deleted_count = result.rowcount

            self.logger.info(
                "Expired sessions deleted successfully",
                deleted_count=deleted_count,
                before_timestamp=before_timestamp.isoformat() if before_timestamp else None
            )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Database error deleting expired sessions",
                before_timestamp=before_timestamp.isoformat() if before_timestamp else None,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def delete_user_sessions(self, user_id: int, except_session_id: Optional[int] = None) -> int:
        """Delete all sessions for a user.

        Args:
            user_id: User ID
            except_session_id: Optional session ID to exclude from deletion

        Returns:
            Number of deleted sessions
        """
        try:
            query = delete(Session).where(Session.user_id == user_id)

            if except_session_id:
                query = query.where(Session.id != except_session_id)

            result = await self.session.execute(query)
            deleted_count = result.rowcount

            self.logger.info(
                "User sessions deleted successfully",
                user_id=user_id,
                deleted_count=deleted_count,
                except_session_id=except_session_id
            )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Database error deleting user sessions",
                user_id=user_id,
                except_session_id=except_session_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def get_session_count(self, user_id: Optional[int] = None, active_only: bool = False) -> int:
        """Get session count with optional filters.

        Args:
            user_id: Optional user ID filter
            active_only: Count only active (non-expired) sessions

        Returns:
            Number of sessions matching filters
        """
        try:
            # Use SQL COUNT for efficiency instead of loading all records
            query = select(func.count(Session.id))

            if user_id:
                query = query.where(Session.user_id == user_id)

            if active_only:
                now = datetime.now(timezone.utc)
                query = query.where(Session.expires_at > now)

            result = await self.session.execute(query)
            count = result.scalar()

            self.logger.debug(
                "Session count retrieved",
                user_id=user_id,
                active_only=active_only,
                count=count
            )

            return count

        except Exception as e:
            self.logger.error(
                "Database error counting sessions",
                user_id=user_id,
                active_only=active_only,
                error=str(e)
            )
            raise

    async def get_valid_session_by_token(
        self,
        session_token: str,
        load_relationships: Optional[List[str]] = None
    ) -> Optional[Session]:
        """Get valid (non-expired) session by token.

        Args:
            session_token: Session token
            load_relationships: List of relationship names to eagerly load

        Returns:
            Session instance or None if not found or expired
        """
        try:
            now = datetime.now(timezone.utc)
            query = select(Session).where(
                and_(
                    Session.session_token == session_token,
                    Session.expires_at > now
                )
            )

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(Session, relationship)))

            result = await self.session.execute(query)
            session = result.scalar_one_or_none()

            if session:
                self.logger.debug("Valid session retrieved by token", session_token=session_token[:8] + "...")
            else:
                self.logger.debug("Valid session not found for token", session_token=session_token[:8] + "...")

            return session

        except Exception as e:
            self.logger.error(
                "Database error retrieving valid session by token",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            raise

    async def get_valid_session_with_user(
        self,
        session_token: str
    ) -> Optional[Session]:
        """Get valid session with user loaded in single query (optimized for auth verification).

        Args:
            session_token: Session token

        Returns:
            Session instance with user relationship loaded, or None if not found or expired
        """
        try:            
            now = datetime.now(timezone.utc)
            query = select(Session).where(
                and_(
                    Session.session_token == session_token,
                    Session.expires_at > now
                )
            ).join(Session.user).where(
                User.is_active == True
            ).options(selectinload(Session.user))  # Load user in same query

            result = await self.session.execute(query)
            session = result.scalar_one_or_none()

            if session:
                self.logger.debug("Valid session with user retrieved",
                                session_token=session_token[:8] + "...",
                                user_id=session.user_id)
            else:
                self.logger.debug("Valid session with active user not found",
                                session_token=session_token[:8] + "...")

            return session

        except Exception as e:
            self.logger.error("Error retrieving session with user",
                            error=str(e),
                            session_token=session_token[:8] + "...")
            raise

    async def create_session_for_user(
        self,
        user_id: int,
        session_token: str,
        ip_address: str,
        user_agent: Optional[str],
        expires_at: datetime,
        commit: bool = True
    ) -> Session:
        """Create a new session for a user.

        Args:
            user_id: User ID
            session_token: Session token
            ip_address: Client IP address
            user_agent: User agent string
            expires_at: Session expiration timestamp
            commit: Whether to commit the transaction

        Returns:
            Created session instance
        """
        try:
            session = Session(
                user_id=user_id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at
            )

            self.session.add(session)

            if commit:
                await self.session.commit()
                await self.session.refresh(session)
            else:
                await self.session.flush()

            self.logger.info(
                "Session created for user",
                session_id=getattr(session, "id", None),
                user_id=user_id
            )

            return session

        except Exception as e:
            self.logger.error(
                "Database error creating session for user",
                user_id=user_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def delete_by_token(self, session_token: str) -> bool:
        """Delete session by token.

        Args:
            session_token: Session token to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            query = delete(Session).where(Session.session_token == session_token)
            result = await self.session.execute(query)

            deleted = result.rowcount > 0

            if deleted:
                self.logger.info("Session deleted by token", session_token=session_token[:8] + "...")
            else:
                self.logger.debug("Session not found for deletion", session_token=session_token[:8] + "...")

            return deleted

        except Exception as e:
            self.logger.error(
                "Database error deleting session by token",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            await self.session.rollback()
            raise