"""Recommendation workflow API endpoints."""

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth.dependencies import (
    check_playlist_creation_rate_limit,
    refresh_spotify_token_if_expired,
    require_auth,
)
from ...core.config import settings
from ...core.constants import PlaylistStatus
from ...core.database import get_db
from ...core.exceptions import (
    InternalServerError,
    NotFoundException,
    ValidationException,
)
from ...core.limiter import limiter
from ...dependencies import get_playlist_repository, get_quota_service
from ...repositories.playlist_repository import PlaylistRepository
from ...models.playlist import Playlist
from ...models.user import User
from ...services.quota_service import QuotaService
from ..core.cache import cache_manager
from ..tools.spotify_service import SpotifyService
from ..tools.reccobeat_service import RecoBeatService
from ..workflows.workflow_manager import WorkflowManager
from .dependencies import get_llm, get_workflow_manager
from .serializers import serialize_playlist_status, serialize_workflow_state

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/recommendations/start")
@limiter.limit(settings.RATE_LIMITS.get("workflow_start", "10/minute"))
async def start_recommendation(
    request: Request,
    mood_prompt: str = Query(..., description="Mood description for playlist generation"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    playlist_repo=Depends(get_playlist_repository),
    quota_service: QuotaService = Depends(get_quota_service),
    _rate_limit_check: None = Depends(check_playlist_creation_rate_limit),
    llm: Any = Depends(get_llm),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Start a new mood-based recommendation workflow."""
    try:
        logger.info(
            "Starting recommendation workflow",
            user_id=current_user.id,
            mood_prompt=mood_prompt,
        )

        current_user = await refresh_spotify_token_if_expired(current_user, db)

        session_id = await workflow_manager.start_workflow(
            mood_prompt=mood_prompt.strip(),
            user_id=str(current_user.id),
            spotify_user_id=current_user.spotify_id,
        )

        state = workflow_manager.get_workflow_state(session_id)
        if state:
            state.metadata["spotify_access_token"] = current_user.access_token

        playlist = await playlist_repo.create_playlist_for_session(
            user_id=current_user.id,
            session_id=session_id,
            mood_prompt=mood_prompt,
            status=PlaylistStatus.PENDING,
            commit=True,
        )

        llm.set_context(
            user_id=current_user.id,
            playlist_id=playlist.id,
            session_id=session_id,
        )

        logger.info("Created playlist record", playlist_id=playlist.id, session_id=session_id)
        await quota_service.increment_daily_usage(current_user.id)

        return {
            "session_id": session_id,
            "status": "started",
            "mood_prompt": mood_prompt,
            "message": "Recommendation workflow started successfully",
        }

    except Exception as exc:
        logger.error("Error starting recommendation workflow", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to start recommendation workflow: {exc}") from exc


@router.get("/recommendations/{session_id}/status")
@limiter.limit(settings.RATE_LIMITS.get("workflow_poll", "60/minute"))
async def get_workflow_status(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Get the current status of a recommendation workflow."""
    try:
        from ...repositories.playlist_repository import PlaylistRepository

        state = workflow_manager.get_workflow_state(session_id)

        if state:
            return serialize_workflow_state(session_id, state)

        playlist_repo = PlaylistRepository(db)
        playlist = await playlist_repo.get_session_status_snapshot(session_id)

        if not playlist:
            raise NotFoundException("Workflow", session_id)

        return serialize_playlist_status(session_id, playlist)

    except NotFoundException:
        raise
    except Exception as exc:
        logger.error("Error getting workflow status", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get workflow status: {exc}") from exc


@router.get("/recommendations/{session_id}/stream")
async def stream_workflow_status(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Stream workflow status updates via Server-Sent Events (SSE)."""

    async def event_generator():
        # Send initial comment to establish connection and prevent buffering
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
        
        def is_forward_progress(current_status: str, new_status: str) -> bool:
            """Check if new_status represents forward progress from current_status."""
            if not current_status:
                return True  # No previous status, allow any
            
            # Define status progression order
            status_order = {
                "pending": 0,
                "analyzing_mood": 1,
                "gathering_seeds": 2,
                "generating_recommendations": 3,
                "evaluating_quality": 4,
                "optimizing_recommendations": 5,
                "ordering_playlist": 5,
                "completed": 6,
                "failed": 6,
                "cancelled": 6,
            }
            
            current_order = status_order.get(current_status, -1)
            new_order = status_order.get(new_status, -1)
            
            # Allow same order (sub-steps) or forward progress
            return new_order >= current_order

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
                from ...repositories.playlist_repository import PlaylistRepository

                playlist_repo = PlaylistRepository(db)
                playlist = await playlist_repo.get_by_session_id(session_id)

                if not playlist:
                    error_data = {"message": f"Workflow {session_id} not found"}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    return

                status_data = serialize_playlist_status(session_id, playlist)
                last_sent_status = playlist.status
                last_sent_step = status_data.get("current_step")

                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"
                
                # Only send complete if status is terminal (completed, failed, cancelled)
                # Otherwise, continue the loop to wait for workflow state updates
                terminal_statuses = [PlaylistStatus.COMPLETED, PlaylistStatus.FAILED, PlaylistStatus.CANCELLED]
                if playlist.status in terminal_statuses:
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering
            "Transfer-Encoding": "chunked",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


@router.delete("/recommendations/{session_id}")
async def cancel_workflow(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Cancel an active workflow."""
    try:
        cancelled = workflow_manager.cancel_workflow(session_id)

        from sqlalchemy import select

        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()

        if playlist:
            playlist.status = PlaylistStatus.CANCELLED
            playlist.error_message = "Workflow cancelled by user"
            await db.commit()
            logger.info("Updated playlist status to cancelled", playlist_id=playlist.id)

        if cancelled or playlist:
            return {
                "session_id": session_id,
                "status": PlaylistStatus.CANCELLED,
                "message": "Workflow cancelled successfully",
            }

        raise NotFoundException("Workflow", session_id)

    except NotFoundException:
        raise
    except Exception as exc:
        logger.error("Error cancelling workflow", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to cancel workflow: {exc}") from exc


@router.get("/recommendations/{session_id}/results")
async def get_workflow_results(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Get the final results of a completed recommendation workflow."""
    try:
        playlist_repo = PlaylistRepository(db)
        playlist = await playlist_repo.get_session_results_snapshot(session_id)

        if playlist and playlist.recommendations_data:
            return {
                "session_id": session_id,
                "status": playlist.status,
                "mood_prompt": playlist.mood_prompt,
                "mood_analysis": playlist.mood_analysis_data,
                "recommendations": playlist.recommendations_data,
                "playlist": (
                    {
                        "id": playlist.spotify_playlist_id,
                        "name": playlist.playlist_data.get("name") if playlist.playlist_data else None,
                        "spotify_url": playlist.playlist_data.get("spotify_url") if playlist.playlist_data else None,
                        "spotify_uri": playlist.playlist_data.get("spotify_uri") if playlist.playlist_data else None,
                    }
                    if playlist.spotify_playlist_id
                    else None
                ),
                "metadata": {},
                "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
                "completed_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
            }

        state = workflow_manager.get_workflow_state(session_id)
        if state:
            return {
                "session_id": session_id,
                "status": state.status.value,
                "mood_prompt": state.mood_prompt,
                "mood_analysis": state.mood_analysis,
                "recommendations": [
                    {
                        "track_id": rec.track_id,
                        "track_name": rec.track_name,
                        "artists": rec.artists,
                        "spotify_uri": rec.spotify_uri,
                        "confidence_score": rec.confidence_score,
                        "reasoning": rec.reasoning,
                        "source": rec.source,
                    }
                    for rec in state.recommendations
                ]
                if state.is_complete() or state.recommendations
                else [],
                "playlist": (
                    {
                        "id": state.playlist_id,
                        "name": state.playlist_name,
                        "spotify_url": state.metadata.get("playlist_url"),
                        "spotify_uri": state.metadata.get("playlist_uri"),
                    }
                    if state.playlist_id
                    else None
                ),
                "metadata": state.metadata,
                "created_at": state.created_at.isoformat(),
                "completed_at": state.updated_at.isoformat() if state.is_complete() else None,
            }

        raise NotFoundException("Workflow", session_id)

    except NotFoundException:
        raise
    except Exception as exc:
        logger.error("Error getting workflow results", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get workflow results: {exc}") from exc


@router.get("/recommendations/{session_id}/cost")
async def get_workflow_cost(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate LLM cost metrics for a workflow session."""
    try:
        from ...repositories.llm_invocation_repository import LLMInvocationRepository

        llm_invocation_repo = LLMInvocationRepository(db)
        summary = await llm_invocation_repo.get_session_cost_summary(session_id)

        if not summary:
            summary = {
                "invocation_count": 0,
                "total_cost_usd": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
            }

        return {
            "session_id": session_id,
            "invocation_count": summary.get("invocation_count", 0),
            "total_llm_cost_usd": summary.get("total_cost_usd", 0.0),
            "total_prompt_tokens": summary.get("total_prompt_tokens", 0),
            "total_completion_tokens": summary.get("total_completion_tokens", 0),
            "total_tokens": summary.get("total_tokens", 0),
        }

    except Exception as exc:
        logger.error("Error getting workflow cost summary", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get workflow cost: {exc}") from exc


@router.get("/recommendations/{session_id}/playlist")
async def get_playlist_details(
    session_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Get detailed playlist information for a completed workflow."""
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise NotFoundException("Workflow", session_id)

        if not state.is_complete() or not state.playlist_id:
            raise ValidationException(f"Playlist not ready for workflow {session_id}")

        tracks = [
            {
                "position": index,
                "track_id": rec.track_id,
                "track_name": rec.track_name,
                "artists": rec.artists,
                "spotify_uri": rec.spotify_uri,
                "confidence_score": rec.confidence_score,
                "reasoning": rec.reasoning,
                "source": rec.source,
            }
            for index, rec in enumerate(state.recommendations)
        ]

        return {
            "session_id": session_id,
            "tracks": tracks,
            "mood_analysis": state.mood_analysis,
            "total_tracks": len(tracks),
            "created_at": state.created_at.isoformat(),
        }

    except (NotFoundException, ValidationException):
        raise
    except Exception as exc:
        logger.error("Error getting playlist details", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get playlist details: {exc}") from exc


@router.post("/recommendations/prefetch-cache")
@limiter.limit(settings.RATE_LIMITS.get("cache_prefetch", "5/minute"))
async def prefetch_user_cache(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Prefetch and warm up user's cache for faster playlist generation.

    Triggered when the user loads the dashboard to hydrate cache with top tracks,
    artists, and audio features in the background.
    """
    try:
        logger.info("Starting cache prefetch", user_id=current_user.id)

        # Refresh token if needed
        current_user = await refresh_spotify_token_if_expired(current_user, db)

        # Initialize services (these would normally be injected)
        spotify_service = SpotifyService()
        reccobeat_service = RecoBeatService()

        # Launch background cache warming (fire-and-forget)
        asyncio.create_task(
            cache_manager.warm_user_cache(
                user_id=str(current_user.id),
                spotify_service=spotify_service,
                reccobeat_service=reccobeat_service,
                access_token=current_user.access_token
            )
        )

        return {
            "status": "prefetch_started",
            "message": "Cache warming initiated in background",
            "user_id": current_user.id
        }

    except Exception as exc:
        logger.error("Error starting cache prefetch", error=str(exc), exc_info=True)
        # Don't fail the request - cache prefetch is best-effort
        return {
            "status": "prefetch_failed",
            "message": "Cache prefetch could not be started",
            "error": str(exc)
        }
