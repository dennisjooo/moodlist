"""Recommendation workflow API endpoints."""

import asyncio
from typing import Any, List, Optional, Dict

import structlog
from fastapi import APIRouter, Depends, Query, Request, WebSocket
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
    UnauthorizedException,
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
from .streaming import create_sse_stream, handle_websocket_connection

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/recommendations/start")
@limiter.limit(settings.RATE_LIMITS.get("workflow_start", "10/minute"))
async def start_recommendation(
    request: Request,
    mood_prompt: str = Query(
        ..., description="Mood description for playlist generation"
    ),
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

        logger.info(
            "Created playlist record", playlist_id=playlist.id, session_id=session_id
        )
        await quota_service.increment_daily_usage(current_user.id)

        return {
            "session_id": session_id,
            "status": "started",
            "mood_prompt": mood_prompt,
            "message": "Recommendation workflow started successfully",
        }

    except Exception as exc:
        logger.error(
            "Error starting recommendation workflow", error=str(exc), exc_info=True
        )
        raise InternalServerError(
            f"Failed to start recommendation workflow: {exc}"
        ) from exc


@router.post("/recommendations/remix")
@limiter.limit(settings.RATE_LIMITS.get("workflow_remix", "5/minute"))
async def remix_playlist(
    request: Request,
    playlist_id: str = Query(..., description="ID of the playlist to remix"),
    source: str = Query(
        "spotify", description="Source of playlist (spotify or moodlist)"
    ),
    mood_prompt: Optional[str] = Query(
        None, description="Optional new mood description"
    ),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    playlist_repo=Depends(get_playlist_repository),
    quota_service: QuotaService = Depends(get_quota_service),
    _rate_limit_check: None = Depends(check_playlist_creation_rate_limit),
    llm: Any = Depends(get_llm),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Start a new workflow based on an existing playlist."""
    try:
        logger.info(
            "Starting remix workflow",
            user_id=current_user.id,
            playlist_id=playlist_id,
            source=source,
            mood_prompt=mood_prompt,
        )

        current_user = await refresh_spotify_token_if_expired(current_user, db)
        if not current_user.access_token:
            raise UnauthorizedException("Failed to obtain valid Spotify access token")

        remix_tracks = []
        original_mood = None

        if source.lower() == "moodlist":
            # Validate input length to prevent DoS
            if len(playlist_id) > 100:
                raise ValidationException("Invalid playlist ID format")
            
            # Try UUID format first (session ID)
            playlist = None
            try:
                import uuid
                uuid.UUID(playlist_id)
                playlist = await playlist_repo.get_by_session_id(playlist_id)
            except ValueError:
                # Try numeric ID
                if playlist_id.isdigit():
                    try:
                        playlist = await playlist_repo.get(int(playlist_id))
                    except (ValueError, OverflowError):
                        raise ValidationException("Playlist ID too large")
                else:
                    raise ValidationException("Invalid playlist ID format")

            if not playlist:
                raise NotFoundException("Playlist", playlist_id)

            # Check ownership - ENFORCE AUTHORIZATION
            if playlist.user_id != current_user.id:
                raise UnauthorizedException("You do not have permission to access this playlist")

            # Extract tracks from recommendations_data
            if playlist.recommendations_data:
                # Transform to SpotifyService track format
                remix_tracks = []
                for rec in playlist.recommendations_data:
                    remix_tracks.append(
                        {
                            "id": rec.get("track_id"),
                            "name": rec.get("track_name"),
                            "artists": rec.get("artists"),
                            "spotify_uri": rec.get("spotify_uri"),
                            "popularity": rec.get("popularity", 50),  # Preserve original popularity
                            "preview_url": rec.get("preview_url"),  # Preserve preview URL
                        }
                    )

            original_mood = playlist.mood_prompt

        elif source.lower() == "spotify":
            spotify_service = SpotifyService()
            remix_tracks = await spotify_service.get_playlist_items(
                access_token=current_user.access_token,
                playlist_id=playlist_id,
                limit=50,  # Reasonable limit for seed tracks
            )
            original_mood = f"Remix of Spotify Playlist {playlist_id}"

        else:
            raise ValidationException(f"Invalid source: {source}")

        if not remix_tracks:
            raise ValidationException("No tracks found in the source playlist to remix")

        # Determine mood prompt
        final_mood_prompt = mood_prompt if mood_prompt else original_mood
        if not final_mood_prompt:
            final_mood_prompt = f"Remix of {source} playlist {playlist_id}"

        # Start workflow
        session_id = await workflow_manager.start_workflow(
            mood_prompt=final_mood_prompt.strip(),
            user_id=str(current_user.id),
            spotify_user_id=current_user.spotify_id,
            remix_tracks=remix_tracks,
        )

        state = workflow_manager.get_workflow_state(session_id)
        if state:
            state.metadata["spotify_access_token"] = current_user.access_token

        playlist = await playlist_repo.create_playlist_for_session(
            user_id=current_user.id,
            session_id=session_id,
            mood_prompt=final_mood_prompt,
            status=PlaylistStatus.PENDING,
            commit=True,
        )

        llm.set_context(
            user_id=current_user.id,
            playlist_id=playlist.id,
            session_id=session_id,
        )

        logger.info(
            "Created playlist record for remix",
            playlist_id=playlist.id,
            session_id=session_id,
        )
        await quota_service.increment_daily_usage(current_user.id)

        return {
            "session_id": session_id,
            "status": "started",
            "mood_prompt": final_mood_prompt,
            "message": "Remix workflow started successfully",
            "source_tracks_count": len(remix_tracks),
        }

    except Exception as exc:
        logger.error(
            "Error starting remix workflow", error=str(exc), exc_info=True
        )
        if isinstance(exc, (NotFoundException, ValidationException, UnauthorizedException)):
            raise
        raise InternalServerError(f"Failed to start remix workflow: {exc}") from exc


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
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """Stream workflow status updates via Server-Sent Events (SSE)."""

    # Verify authorization BEFORE starting stream to avoid blocking inside generator
    from ...repositories.playlist_repository import PlaylistRepository

    playlist_repo = PlaylistRepository(db)
    session_playlist = await playlist_repo.get_by_session_id(session_id)

    if session_playlist and session_playlist.user_id != current_user.id:
        raise UnauthorizedException("Unauthorized access to workflow")

    return StreamingResponse(
        create_sse_stream(session_id, request, session_playlist, workflow_manager),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering
            "X-Content-Type-Options": "nosniff",  # Prevent MIME sniffing
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


@router.websocket("/recommendations/{session_id}/ws")
async def websocket_workflow_status(
    websocket: WebSocket,
    session_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """WebSocket endpoint for workflow status updates (Cloudflare-friendly alternative to SSE)."""
    await handle_websocket_connection(websocket, session_id, workflow_manager)


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
                        "name": playlist.playlist_data.get("name")
                        if playlist.playlist_data
                        else None,
                        "spotify_url": playlist.playlist_data.get("spotify_url")
                        if playlist.playlist_data
                        else None,
                        "spotify_uri": playlist.playlist_data.get("spotify_uri")
                        if playlist.playlist_data
                        else None,
                    }
                    if playlist.spotify_playlist_id
                    else None
                ),
                "metadata": {},
                "created_at": playlist.created_at.isoformat()
                if playlist.created_at
                else None,
                "completed_at": playlist.updated_at.isoformat()
                if playlist.updated_at
                else None,
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
                "completed_at": state.updated_at.isoformat()
                if state.is_complete()
                else None,
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
        logger.error(
            "Error getting workflow cost summary", error=str(exc), exc_info=True
        )
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
                access_token=current_user.access_token,
            )
        )

        return {
            "status": "prefetch_started",
            "message": "Cache warming initiated in background",
            "user_id": current_user.id,
        }

    except Exception as exc:
        logger.error("Error starting cache prefetch", error=str(exc), exc_info=True)
        # Don't fail the request - cache prefetch is best-effort
        return {
            "status": "prefetch_failed",
            "message": "Cache prefetch could not be started",
            "error": str(exc),
        }
