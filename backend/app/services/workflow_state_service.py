"""Workflow state service for workflow state management."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import structlog

from app.repositories.session_repository import SessionRepository
from app.repositories.playlist_repository import PlaylistRepository
from app.repositories.user_repository import UserRepository
from app.core.exceptions import NotFoundException, ValidationException
from app.core.constants import RecommendationStatusEnum

logger = structlog.get_logger(__name__)


class WorkflowStateService:
    """Service for managing workflow state operations."""

    def __init__(
        self,
        session_repository: SessionRepository,
        playlist_repository: PlaylistRepository,
        user_repository: UserRepository,
    ):
        """Initialize the workflow state service.

        Args:
            session_repository: Session repository
            playlist_repository: Playlist repository
            user_repository: User repository
        """
        self.session_repository = session_repository
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
        self.logger = logger.bind(service="WorkflowStateService")

    async def get_workflow_state(self, session_id: str, user_id: int) -> Dict[str, Any]:
        """Get the current state of a workflow session.

        Args:
            session_id: Workflow session ID
            user_id: User ID (for ownership validation)

        Returns:
            Workflow state data

        Raises:
            NotFoundException: If session not found or doesn't belong to user
        """
        try:
            # Get session
            session = await self.session_repository.get_by_token(session_id)
            if not session:
                raise NotFoundException("Session", session_id)

            # Validate ownership
            if session.user_id != user_id:
                raise NotFoundException("Session", session_id)

            # Get associated playlist if exists
            playlist = None
            if session.metadata and session.metadata.get("playlist_id"):
                try:
                    playlist = await self.playlist_repository.get_by_id(
                        session.metadata["playlist_id"]
                    )
                except Exception:
                    # Playlist might not exist, that's okay
                    pass

            # Build state response
            state_data = {
                "session_id": session.session_token,
                "user_id": session.user_id,
                "status": session.metadata.get("status", "unknown")
                if session.metadata
                else "unknown",
                "current_step": session.metadata.get("current_step")
                if session.metadata
                else None,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "metadata": session.metadata or {},
            }

            # Add playlist info if available
            if playlist:
                state_data["playlist"] = {
                    "id": playlist.id,
                    "spotify_id": playlist.spotify_playlist_id,
                    "name": playlist.name,
                    "status": playlist.status,
                    "track_count": playlist.track_count,
                }

            return state_data

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to get workflow state",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def update_workflow_status(
        self,
        session_id: str,
        user_id: int,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update workflow status and metadata.

        Args:
            session_id: Workflow session ID
            user_id: User ID (for ownership validation)
            status: New status
            current_step: Current workflow step
            error_message: Optional error message
            metadata: Additional metadata to merge

        Returns:
            Updated workflow state

        Raises:
            NotFoundException: If session not found or doesn't belong to user
            ValidationException: If status is invalid
        """
        try:
            # Validate status
            if status not in [s.value for s in RecommendationStatusEnum]:
                raise ValidationException(f"Invalid status: {status}")

            # Get session
            session = await self.session_repository.get_by_token(session_id)
            if not session:
                raise NotFoundException("Session", session_id)

            # Validate ownership
            if session.user_id != user_id:
                raise NotFoundException("Session", session_id)

            # Prepare metadata update
            current_metadata = session.metadata or {}
            updated_metadata = current_metadata.copy()

            updated_metadata["status"] = status
            if current_step is not None:
                updated_metadata["current_step"] = current_step
            if error_message is not None:
                updated_metadata["error_message"] = error_message
                updated_metadata["error_timestamp"] = datetime.now(
                    timezone.utc
                ).isoformat()
            if metadata:
                updated_metadata.update(metadata)

            # Update session
            await self.session_repository.update(session.id, metadata=updated_metadata)

            # Update last activity
            await self.session_repository.update_last_activity(session.id)

            self.logger.info(
                "Updated workflow status",
                session_id=session_id,
                user_id=user_id,
                status=status,
                current_step=current_step,
            )

            return await self.get_workflow_state(session_id, user_id)

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            self.logger.error(
                "Failed to update workflow status",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def associate_playlist_with_session(
        self, session_id: str, user_id: int, playlist_id: int
    ) -> Dict[str, Any]:
        """Associate a playlist with a workflow session.

        Args:
            session_id: Workflow session ID
            user_id: User ID (for ownership validation)
            playlist_id: Playlist ID

        Returns:
            Updated workflow state

        Raises:
            NotFoundException: If session or playlist not found
            ValidationException: If playlist doesn't belong to user
        """
        try:
            # Get and validate session
            session = await self.session_repository.get_by_token(session_id)
            if not session:
                raise NotFoundException("Session", session_id)

            if session.user_id != user_id:
                raise NotFoundException("Session", session_id)

            # Get and validate playlist
            playlist = await self.playlist_repository.get_by_id_or_fail(playlist_id)

            if playlist.user_id != user_id:
                raise ValidationException("Playlist does not belong to user")

            # Update session metadata
            current_metadata = session.metadata or {}
            updated_metadata = current_metadata.copy()
            updated_metadata["playlist_id"] = playlist_id
            updated_metadata["spotify_playlist_id"] = playlist.spotify_playlist_id

            await self.session_repository.update(session.id, metadata=updated_metadata)

            # Update playlist with session reference
            await self.playlist_repository.update(playlist_id, session_id=session_id)

            self.logger.info(
                "Associated playlist with session",
                session_id=session_id,
                playlist_id=playlist_id,
                user_id=user_id,
            )

            return await self.get_workflow_state(session_id, user_id)

        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            self.logger.error(
                "Failed to associate playlist with session",
                session_id=session_id,
                playlist_id=playlist_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def get_user_active_sessions(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get active workflow sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to return

        Returns:
            List of active session data
        """
        try:
            sessions = await self.session_repository.get_active_sessions(
                user_id=user_id, limit=limit
            )

            return [
                {
                    "session_id": s.session_token,
                    "status": s.metadata.get("status", "unknown")
                    if s.metadata
                    else "unknown",
                    "current_step": s.metadata.get("current_step")
                    if s.metadata
                    else None,
                    "created_at": s.created_at.isoformat(),
                    "last_activity": s.last_activity.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                }
                for s in sessions
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get user active sessions", user_id=user_id, error=str(e)
            )
            raise

    async def cleanup_expired_sessions(
        self, before_timestamp: Optional[datetime] = None
    ) -> int:
        """Clean up expired sessions.

        Args:
            before_timestamp: Optional timestamp to clean sessions expired before this time

        Returns:
            Number of sessions deleted
        """
        try:
            deleted_count = await self.session_repository.delete_expired_sessions(
                before_timestamp
            )

            self.logger.info(
                "Cleaned up expired sessions",
                deleted_count=deleted_count,
                before_timestamp=before_timestamp.isoformat()
                if before_timestamp
                else None,
            )

            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup expired sessions", error=str(e))
            raise

    async def extend_session(
        self, session_id: str, user_id: int, new_expires_at: datetime
    ) -> Dict[str, Any]:
        """Extend session expiration time.

        Args:
            session_id: Workflow session ID
            user_id: User ID (for ownership validation)
            new_expires_at: New expiration timestamp

        Returns:
            Updated workflow state

        Raises:
            NotFoundException: If session not found or doesn't belong to user
        """
        try:
            # Get session
            session = await self.session_repository.get_by_token(session_id)
            if not session:
                raise NotFoundException("Session", session_id)

            # Validate ownership
            if session.user_id != user_id:
                raise NotFoundException("Session", session_id)

            # Extend session
            await self.session_repository.extend_session(session.id, new_expires_at)

            self.logger.info(
                "Extended session expiration",
                session_id=session_id,
                user_id=user_id,
                new_expires_at=new_expires_at.isoformat(),
            )

            return await self.get_workflow_state(session_id, user_id)

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to extend session",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise
