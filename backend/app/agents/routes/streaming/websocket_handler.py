"""WebSocket handler for workflow status updates."""

import asyncio

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from ....core.constants import PlaylistStatus
from ...workflows.workflow_manager import WorkflowManager
from ..serializers import serialize_workflow_state
from .streaming_utils import is_forward_progress
from .websocket_auth import authenticate_websocket

logger = structlog.get_logger(__name__)


async def handle_websocket_connection(
    websocket: WebSocket,
    session_id: str,
    workflow_manager: WorkflowManager,
):
    """
    Handle WebSocket connection for workflow status updates.

    Args:
        websocket: WebSocket connection
        session_id: Workflow session ID
        workflow_manager: Workflow manager instance
    """
    await websocket.accept()

    logger.info("WebSocket connection accepted", session_id=session_id)

    try:
        # Authenticate and get initial playlist data
        (
            current_user,
            initial_playlist_data,
            initial_playlist_status,
        ) = await authenticate_websocket(websocket, session_id)

        # Send initial connected message
        await websocket.send_json({"type": "connected", "session_id": session_id})

        # Set up state change subscription
        queue: asyncio.Queue = asyncio.Queue()
        last_sent_status = None
        last_sent_step = None

        async def state_change_callback(sid: str, state):
            logger.info(
                "WebSocket received state change notification",
                session_id=sid,
                status=state.status.value if state else None,
                current_step=state.current_step if state else None,
            )
            await queue.put(state)
            logger.info(
                "WebSocket state added to queue",
                session_id=sid,
                queue_size=queue.qsize(),
            )

        workflow_manager.subscribe_to_state_changes(session_id, state_change_callback)
        logger.info("WebSocket subscribed to state changes", session_id=session_id)

        def get_current_state():
            return workflow_manager.get_workflow_state(session_id)

        try:
            # Send initial state
            state = get_current_state()
            if state:
                status_data = serialize_workflow_state(session_id, state)
                last_sent_status = state.status.value
                last_sent_step = state.current_step
                await websocket.send_json({"type": "status", "data": status_data})

                if state.status.value in ["completed", "failed", "cancelled"]:
                    await websocket.send_json({"type": "complete", "data": status_data})
                    await websocket.close(code=1000)
                    return
            elif initial_playlist_data:
                last_sent_status = initial_playlist_status
                last_sent_step = initial_playlist_data.get("current_step")
                await websocket.send_json(
                    {"type": "status", "data": initial_playlist_data}
                )

                terminal_statuses = [
                    PlaylistStatus.COMPLETED,
                    PlaylistStatus.FAILED,
                    PlaylistStatus.CANCELLED,
                ]
                if initial_playlist_status in terminal_statuses:
                    await websocket.send_json(
                        {"type": "complete", "data": initial_playlist_data}
                    )
                    await websocket.close(code=1000)
                    return

            # Main loop: process updates
            while True:
                try:
                    # Wait for state change or client message
                    pending_tasks = [
                        asyncio.create_task(queue.get()),
                        asyncio.create_task(websocket.receive_text()),
                    ]
                    done, pending = await asyncio.wait(
                        pending_tasks, timeout=30, return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, WebSocketDisconnect):
                            pass

                    if not done:
                        # Timeout - send keep-alive
                        await websocket.send_json({"type": "ping"})
                        continue

                    # Check if it's a state update
                    for task in done:
                        try:
                            result = task.result()
                            logger.info(
                                "WebSocket processing task result",
                                session_id=session_id,
                                result_type=type(result).__name__,
                            )
                            if isinstance(result, str):
                                # Client message (ping/pong)
                                logger.debug(
                                    "WebSocket received client message",
                                    session_id=session_id,
                                    message=result,
                                )
                                if result == "ping":
                                    await websocket.send_json({"type": "pong"})
                                continue

                            # State update
                            logger.info(
                                "WebSocket processing state update",
                                session_id=session_id,
                            )
                            current_state = get_current_state() or result

                            if (
                                current_state.status.value != last_sent_status
                                or current_state.current_step != last_sent_step
                            ):
                                logger.info(
                                    "WebSocket detected state change",
                                    session_id=session_id,
                                    old_status=last_sent_status,
                                    new_status=current_state.status.value,
                                    old_step=last_sent_step,
                                    new_step=current_state.current_step,
                                )

                                if is_forward_progress(
                                    last_sent_status, current_state.status.value
                                ):
                                    status_data = serialize_workflow_state(
                                        session_id, current_state
                                    )
                                    last_sent_status = current_state.status.value
                                    last_sent_step = current_state.current_step

                                    logger.info(
                                        "WebSocket sending status update",
                                        session_id=session_id,
                                        status=current_state.status.value,
                                        step=current_state.current_step,
                                    )
                                    await websocket.send_json(
                                        {"type": "status", "data": status_data}
                                    )

                                    if current_state.status.value in [
                                        "completed",
                                        "failed",
                                        "cancelled",
                                    ]:
                                        await websocket.send_json(
                                            {"type": "complete", "data": status_data}
                                        )
                                        await websocket.close(code=1000)
                                        return
                        except WebSocketDisconnect:
                            # Client disconnected while processing - exit loop
                            logger.info(
                                "Client disconnected during message processing",
                                session_id=session_id,
                            )
                            return
                        except Exception as e:
                            logger.error(
                                "Error processing WebSocket task", error=str(e)
                            )

                except asyncio.TimeoutError:
                    # Send keep-alive
                    try:
                        await websocket.send_json({"type": "ping"})
                    except WebSocketDisconnect:
                        logger.info(
                            "Client disconnected during ping", session_id=session_id
                        )
                        return
                except WebSocketDisconnect:
                    # Client disconnected - exit cleanly
                    logger.info(
                        "Client disconnected in main loop", session_id=session_id
                    )
                    return

        finally:
            workflow_manager.unsubscribe_from_state_changes(
                session_id, state_change_callback
            )
            logger.debug("Unsubscribed from state changes", session_id=session_id)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", session_id=session_id)
    except ValueError:
        # Authentication errors are already handled in authenticate_websocket
        pass
    except Exception as exc:
        logger.error(
            "WebSocket error", session_id=session_id, error=str(exc), exc_info=True
        )
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=1011)
        except Exception:
            pass
