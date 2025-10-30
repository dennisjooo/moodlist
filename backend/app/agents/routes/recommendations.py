"""Recommendation workflow API endpoints."""

import asyncio
import json
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
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
from ...dependencies import get_playlist_repository
from ...models.playlist import Playlist
from ...models.user import User
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
    background_tasks: Optional[BackgroundTasks] = None,
    db: AsyncSession = Depends(get_db),
    playlist_repo=Depends(get_playlist_repository),
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

        llm.set_db_session(db)

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
        from ...repositories.llm_invocation_repository import LLMInvocationRepository
        from ...repositories.playlist_repository import PlaylistRepository

        llm_invocation_repo = LLMInvocationRepository(db)
        session_cost_summary = await llm_invocation_repo.get_session_cost_summary(session_id)

        state = workflow_manager.get_workflow_state(session_id)

        if state:
            return serialize_workflow_state(session_id, state, session_cost_summary)

        playlist_repo = PlaylistRepository(db)
        playlist = await playlist_repo.get_by_session_id(session_id)

        if not playlist:
            raise NotFoundException("Workflow", session_id)

        return serialize_playlist_status(session_id, playlist, session_cost_summary)

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
        queue: asyncio.Queue = asyncio.Queue()

        async def state_change_callback(sid: str, state):
            await queue.put(state)

        workflow_manager.subscribe_to_state_changes(session_id, state_change_callback)

        try:
            state = workflow_manager.get_workflow_state(session_id)

            if state:
                status_data = serialize_workflow_state(session_id, state)

                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

                if state.status.value in ["completed", "failed"]:
                    yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                    return
            else:
                from ...repositories.playlist_repository import PlaylistRepository

                playlist_repo = PlaylistRepository(db)
                playlist = await playlist_repo.get_by_session_id(session_id)

                if not playlist:
                    error_data = {"message": f"Workflow {session_id} not found"}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    return

                status_data = serialize_playlist_status(session_id, playlist)

                yield f"event: status\ndata: {json.dumps(status_data)}\n\n"
                yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                return

            while True:
                if await request.is_disconnected():
                    logger.debug(
                        "Client disconnected from SSE stream",
                        session_id=session_id,
                    )
                    break

                try:
                    updated_state = await asyncio.wait_for(queue.get(), timeout=15.0)
                    status_data = serialize_workflow_state(session_id, updated_state)
                    yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

                    if updated_state.status.value in ["completed", "failed"]:
                        yield f"event: complete\ndata: {json.dumps(status_data)}\n\n"
                        break

                except asyncio.TimeoutError:
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
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
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
        from sqlalchemy import select

        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()

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
