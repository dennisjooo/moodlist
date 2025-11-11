"""SSE (Server-Sent Events) handler for workflow status streaming."""

import asyncio
import json

import structlog
from fastapi import Request

from ....core.constants import PlaylistStatus
from ....models.playlist import Playlist
from ...workflows.workflow_manager import WorkflowManager
from ..serializers import serialize_playlist_status, serialize_workflow_state
from .streaming_utils import is_forward_progress

logger = structlog.get_logger(__name__)


async def create_sse_stream(
    session_id: str,
    request: Request,
    session_playlist: Playlist | None,
    workflow_manager: WorkflowManager,
):
    """
    Generate SSE events for workflow status updates.
    
    Args:
        session_id: Workflow session ID
        request: FastAPI request object (for disconnect detection)
        session_playlist: Playlist record from database (if available)
        workflow_manager: Workflow manager instance
    """
    # Send initial connection message with padding to prevent Cloudflare buffering
    # Cloudflare requires larger padding (8KB) to disable buffering for SSE
    yield ": " + (" " * 8192) + "\n\n"
    yield ": connected\n\n"

    queue: asyncio.Queue = asyncio.Queue()
    last_sent_status = None
    last_sent_step = None

    async def state_change_callback(sid: str, state):
        await queue.put(state)

    workflow_manager.subscribe_to_state_changes(session_id, state_change_callback)

    def get_current_state():
        """Get the current state from workflow manager, checking both active and completed."""
        return workflow_manager.get_workflow_state(session_id)

    try:
        # Get initial state
        state = get_current_state()

        if state:
            status_data = serialize_workflow_state(session_id, state)
            last_sent_status = state.status.value
            last_sent_step = state.current_step

            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

            if state.status.value in ["completed", "failed", "cancelled"]:
                yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                return
        else:
            # Workflow state not found in memory - check database as fallback
            # Use the session_playlist we already fetched during auth check
            if not session_playlist:
                error_data = {"message": f"Workflow {session_id} not found"}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                return

            status_data = serialize_playlist_status(session_id, session_playlist)
            last_sent_status = session_playlist.status
            last_sent_step = status_data.get("current_step")

            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

            # Only send complete if status is terminal (completed, failed, cancelled)
            # Otherwise, continue the loop to wait for workflow state updates
            terminal_statuses = [PlaylistStatus.COMPLETED, PlaylistStatus.FAILED, PlaylistStatus.CANCELLED]
            if session_playlist.status in terminal_statuses:
                yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                return
            # If not terminal, continue to main loop to wait for state updates

        # Main loop: process queued updates and periodically verify current state
        while True:
            if await request.is_disconnected():
                logger.debug(
                    "Client disconnected from SSE stream",
                    session_id=session_id,
                )
                break

            try:
                # Wait for state change notification with timeout
                updated_state = await asyncio.wait_for(queue.get(), timeout=5.0)
                
                # Always get the latest state from workflow manager to ensure accuracy
                current_state = get_current_state()
                if current_state:
                    # Use the current state from manager (most up-to-date)
                    state_to_send = current_state
                else:
                    # Fallback to queued state if manager doesn't have it
                    state_to_send = updated_state
                
                # Only send if status or step actually changed AND it's forward progress
                if (state_to_send.status.value != last_sent_status or 
                    state_to_send.current_step != last_sent_step):
                    
                    # Check if this is forward progress (prevent backwards updates)
                    if is_forward_progress(last_sent_status, state_to_send.status.value):
                        status_data = serialize_workflow_state(session_id, state_to_send)
                        last_sent_status = state_to_send.status.value
                        last_sent_step = state_to_send.current_step
                        
                        yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

                        if state_to_send.status.value in ["completed", "failed", "cancelled"]:
                            yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                            break
                    else:
                        logger.debug(
                            "Skipping backwards status update in stream",
                            session_id=session_id,
                            from_status=last_sent_status,
                            to_status=state_to_send.status.value
                        )

            except asyncio.TimeoutError:
                # On timeout, verify current state hasn't changed
                current_state = get_current_state()
                if current_state:
                    # Check if state changed while we were waiting AND it's forward progress
                    if (current_state.status.value != last_sent_status or 
                        current_state.current_step != last_sent_step):
                        
                        # Check if this is forward progress
                        if is_forward_progress(last_sent_status, current_state.status.value):
                            status_data = serialize_workflow_state(session_id, current_state)
                            last_sent_status = current_state.status.value
                            last_sent_step = current_state.current_step
                            
                            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

                            if current_state.status.value in ["completed", "failed", "cancelled"]:
                                yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                                break
                        else:
                            logger.debug(
                                "Skipping backwards status update in stream (timeout check)",
                                session_id=session_id,
                                from_status=last_sent_status,
                                to_status=current_state.status.value
                            )
                
                # Send keep-alive
                yield ": keep-alive\n\n"

    except Exception as exc:
        logger.error(
            "Error in SSE stream",
            session_id=session_id,
            error=str(exc),
            exc_info=True,
        )
        error_data = {"message": str(exc)}
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    finally:
        workflow_manager.unsubscribe_from_state_changes(session_id, state_change_callback)
        logger.debug("Unsubscribed from state changes", session_id=session_id)

