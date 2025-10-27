"""Workflow state management."""

import structlog
from typing import Callable, Awaitable, Dict, List
from datetime import datetime, timezone

from sqlalchemy import select

from ..states.agent_state import AgentState

logger = structlog.get_logger(__name__)

# Type alias for state change callback
StateChangeCallback = Callable[[str, AgentState], Awaitable[None]]


class WorkflowStateManager:
    """Manages workflow state and subscriptions."""

    def __init__(self):
        """Initialize the workflow state manager."""
        # Workflow state
        self.active_workflows: Dict[str, AgentState] = {}
        self.completed_workflows: Dict[str, AgentState] = {}

        # State change notifications for SSE
        self.state_change_callbacks: Dict[str, List[StateChangeCallback]] = {}

    def subscribe_to_state_changes(self, session_id: str, callback: StateChangeCallback):
        """Subscribe to state changes for a specific workflow session.

        Args:
            session_id: Workflow session ID to subscribe to
            callback: Async callback function to call when state changes
        """
        if session_id not in self.state_change_callbacks:
            self.state_change_callbacks[session_id] = []
        self.state_change_callbacks[session_id].append(callback)
        logger.debug(f"Added state change callback for session {session_id}")

    def unsubscribe_from_state_changes(self, session_id: str, callback: StateChangeCallback):
        """Unsubscribe from state changes for a specific workflow session.

        Args:
            session_id: Workflow session ID to unsubscribe from
            callback: Callback function to remove
        """
        if session_id in self.state_change_callbacks:
            try:
                self.state_change_callbacks[session_id].remove(callback)
                if not self.state_change_callbacks[session_id]:
                    del self.state_change_callbacks[session_id]
                logger.debug(f"Removed state change callback for session {session_id}")
            except ValueError:
                pass

    async def notify_state_change(self, session_id: str, state: AgentState):
        """Notify all subscribers of a state change.

        Args:
            session_id: Workflow session ID
            state: Updated workflow state
        """
        if session_id in self.state_change_callbacks:
            callbacks = self.state_change_callbacks[session_id].copy()
            for callback in callbacks:
                try:
                    await callback(session_id, state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {str(e)}", exc_info=True)

    async def update_state(self, session_id: str, state: AgentState):
        """Update workflow state and notify subscribers.

        Args:
            session_id: Workflow session ID
            state: Updated workflow state
        """
        self.active_workflows[session_id] = state
        await self.update_playlist_db(session_id, state)
        await self.notify_state_change(session_id, state)

    async def update_playlist_db(self, session_id: str, state: AgentState) -> None:
        """Update the playlist database with workflow state.

        Args:
            session_id: Workflow session ID
            state: Current workflow state
        """
        try:
            from ...core.database import async_session_factory
            from ...models.playlist import Playlist

            async with async_session_factory() as db:
                # Find the playlist by session_id
                result = await db.execute(
                    select(Playlist).where(Playlist.session_id == session_id)
                )
                playlist = result.scalar_one_or_none()

                if playlist:
                    # Update status
                    playlist.status = state.status.value

                    # Update mood analysis if available
                    if state.mood_analysis:
                        playlist.mood_analysis_data = state.mood_analysis

                        # Extract and store color scheme if present
                        color_scheme = state.mood_analysis.get("color_scheme", {})
                        if color_scheme:
                            playlist.color_primary = color_scheme.get("primary")
                            playlist.color_secondary = color_scheme.get("secondary")
                            playlist.color_tertiary = color_scheme.get("tertiary")

                    # Update recommendations if available
                    if state.recommendations:
                        playlist.recommendations_data = [
                            {
                                "track_id": rec.track_id,
                                "track_name": rec.track_name,
                                "artists": rec.artists,
                                "spotify_uri": rec.spotify_uri,
                                "confidence_score": rec.confidence_score,
                                "reasoning": rec.reasoning,
                                "source": rec.source
                            }
                            for rec in state.recommendations
                        ]
                        playlist.track_count = len(state.recommendations)

                    # Update playlist metadata if created
                    if state.playlist_id:
                        playlist.spotify_playlist_id = state.playlist_id
                        playlist.playlist_data = {
                            "name": state.playlist_name,
                            "spotify_url": state.metadata.get("playlist_url"),
                            "spotify_uri": state.metadata.get("playlist_uri")
                        }

                    # Update error if present
                    if state.error_message:
                        playlist.error_message = state.error_message

                    await db.commit()
                    logger.debug(f"Updated playlist DB for session {session_id}")
                else:
                    logger.warning(f"Playlist not found for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to update playlist DB for session {session_id}: {str(e)}", exc_info=True)

    def move_to_completed(self, session_id: str, state: AgentState):
        """Move workflow from active to completed.

        Args:
            session_id: Workflow session ID
            state: Final workflow state
        """
        if session_id in self.active_workflows:
            self.completed_workflows[session_id] = self.active_workflows.pop(session_id)

    def cleanup_old_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour - max_age_hours
        )

        to_remove = []
        for session_id, state in self.completed_workflows.items():
            if state.created_at < cutoff_time:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.completed_workflows[session_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old workflows")

