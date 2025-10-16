"""Playlist CRUD routes for managing user playlists."""

import structlog
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from langchain_openai import ChatOpenAI
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.constants import PlaylistStatus
from ..core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
    InternalServerError
)
from ..auth.dependencies import require_auth, refresh_spotify_token_if_expired
from ..models.user import User
from ..models.playlist import Playlist
from .services.playlist_creation_service import PlaylistCreationService
from ..agents.workflows.workflow_manager import WorkflowManager
from ..agents.states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
from ..agents.tools.reccobeat_service import RecoBeatService
from ..agents.tools.spotify_service import SpotifyService
from ..core.config import settings
from .services import CompletedPlaylistEditor


logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services and dependencies
reccobeat_service = RecoBeatService()
spotify_service = SpotifyService()

groq_llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    temperature=1,
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY
)

# Initialize playlist services
completed_playlist_editor = CompletedPlaylistEditor()
playlist_creation_service = PlaylistCreationService(spotify_service, groq_llm, verbose=False)


@router.get("/playlists")
async def get_user_playlists(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    status: Optional[str] = Query(default=None, description="Filter by status (pending, completed, failed)")
):
    """Get all playlists created by the current user.

    Args:
        current_user: Authenticated user
        db: Database session
        limit: Maximum number of playlists to return
        offset: Number of playlists to skip
        status: Optional status filter

    Returns:
        List of user's playlists with pagination info
    """
    try:
        # Build query - exclude soft-deleted and cancelled playlists
        query = (
            select(Playlist)
            .where(
                Playlist.user_id == current_user.id,
                Playlist.deleted_at.is_(None),
                Playlist.status != PlaylistStatus.CANCELLED
            )
        )
        
        # Add status filter if provided
        if status:
            query = query.where(Playlist.status == status)
        
        # Add ordering and pagination
        query = query.order_by(desc(Playlist.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        playlists = result.scalars().all()
        
        # Format playlists for response
        playlists_data = []
        for playlist in playlists:
            playlist_info = {
                "id": playlist.id,
                "session_id": playlist.session_id,
                "mood_prompt": playlist.mood_prompt,
                "status": playlist.status,
                "track_count": playlist.track_count,
                "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
                "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
            }
            
            # Add playlist data if available
            if playlist.playlist_data:
                playlist_info["name"] = playlist.playlist_data.get("name")
                playlist_info["spotify_url"] = playlist.playlist_data.get("spotify_url")
                playlist_info["spotify_uri"] = playlist.playlist_data.get("spotify_uri")
            
            # Add spotify playlist id if available
            if playlist.spotify_playlist_id:
                playlist_info["spotify_playlist_id"] = playlist.spotify_playlist_id
            
            # Add mood analysis data if available
            if playlist.mood_analysis_data:
                playlist_info["mood_analysis_data"] = playlist.mood_analysis_data
            
            playlists_data.append(playlist_info)
        
        # Get total count for pagination - exclude soft-deleted and cancelled playlists
        count_query = select(func.count()).select_from(Playlist).where(
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None),
            Playlist.status != PlaylistStatus.CANCELLED
        )
        if status:
            count_query = count_query.where(Playlist.status == status)
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return {
            "playlists": playlists_data,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting user playlists: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get user playlists: {str(e)}")


@router.get("/playlists/{playlist_id}")
async def get_playlist(
    playlist_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific playlist by ID.

    Args:
        playlist_id: Playlist database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Playlist details
    """
    try:
        query = select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None)
        )
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))
        
        return {
            "id": playlist.id,
            "session_id": playlist.session_id,
            "mood_prompt": playlist.mood_prompt,
            "status": playlist.status,
            "track_count": playlist.track_count,
            "duration_ms": playlist.duration_ms,
            "playlist_data": playlist.playlist_data,
            "recommendations_data": playlist.recommendations_data,
            "mood_analysis_data": playlist.mood_analysis_data,
            "spotify_playlist_id": playlist.spotify_playlist_id,
            "error_message": playlist.error_message,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
        }

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist {playlist_id}: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get playlist: {str(e)}")


@router.get("/playlists/session/{session_id}")
async def get_playlist_by_session(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get a playlist by its session ID.

    Args:
        session_id: Workflow session UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Playlist details
    """
    try:
        query = select(Playlist).where(
            Playlist.session_id == session_id,
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None)
        )
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise NotFoundException("Playlist", session_id)
        
        return {
            "id": playlist.id,
            "session_id": playlist.session_id,
            "mood_prompt": playlist.mood_prompt,
            "status": playlist.status,
            "track_count": playlist.track_count,
            "duration_ms": playlist.duration_ms,
            "playlist_data": playlist.playlist_data,
            "recommendations_data": playlist.recommendations_data,
            "mood_analysis_data": playlist.mood_analysis_data,
            "spotify_playlist_id": playlist.spotify_playlist_id,
            "error_message": playlist.error_message,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
        }

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist by session {session_id}: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get playlist: {str(e)}")


@router.delete("/playlists/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a playlist.

    Args:
        playlist_id: Playlist database ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    try:
        query = select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None)
        )
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))
        
        # Soft delete by setting deleted_at timestamp
        playlist.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Soft deleted playlist {playlist_id} for user {current_user.id}")
        
        return {
            "message": "Playlist deleted successfully",
            "playlist_id": playlist_id
        }

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist {playlist_id}: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to delete playlist: {str(e)}")


@router.get("/playlists/stats/summary")
async def get_playlist_stats(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's playlist statistics.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Playlist statistics
    """
    try:
        # Total playlists - exclude soft-deleted
        total_query = select(func.count()).select_from(Playlist).where(
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None)
        )
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        # Completed playlists - exclude soft-deleted
        completed_query = select(func.count()).select_from(Playlist).where(
            Playlist.user_id == current_user.id,
            Playlist.status == PlaylistStatus.COMPLETED,
            Playlist.deleted_at.is_(None)
        )
        completed_result = await db.execute(completed_query)
        completed = completed_result.scalar()
        
        # Total tracks - exclude soft-deleted
        tracks_query = select(func.sum(Playlist.track_count)).where(
            Playlist.user_id == current_user.id,
            Playlist.deleted_at.is_(None)
        )
        tracks_result = await db.execute(tracks_query)
        total_tracks = tracks_result.scalar() or 0
        
        return {
            "total_playlists": total,
            "completed_playlists": completed,
            "total_tracks": total_tracks,
            "user_id": current_user.id
        }

    except Exception as e:
        logger.error(f"Error getting playlist stats: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get playlist stats: {str(e)}")


@router.get("/stats/public")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """Get public platform statistics (no authentication required).

    Args:
        db: Database session

    Returns:
        Public platform statistics including total users and playlists count
    """
    try:
        # Total users
        total_users_query = select(func.count()).select_from(User).where(User.is_active == True)
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar()
        
        # Total playlists
        total_playlists_query = select(func.count()).select_from(Playlist)
        total_playlists_result = await db.execute(total_playlists_query)
        total_playlists = total_playlists_result.scalar()
        
        # Completed playlists
        completed_playlists_query = select(func.count()).select_from(Playlist).where(
            Playlist.status == PlaylistStatus.COMPLETED
        )
        completed_playlists_result = await db.execute(completed_playlists_query)
        completed_playlists = completed_playlists_result.scalar()
        
        return {
            "total_users": total_users,
            "total_playlists": total_playlists,
            "completed_playlists": completed_playlists
        }

    except Exception as e:
        logger.error(f"Error getting public stats: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get public stats: {str(e)}")


@router.post("/playlists/{session_id}/edit")
async def edit_playlist(
    session_id: str,
    edit_type: str = Query(..., description="Type of edit (reorder/remove/add)"),
    track_id: Optional[str] = Query(None, description="Track ID for edit"),
    new_position: Optional[int] = Query(None, description="New position for reorder"),
    track_uri: Optional[str] = Query(None, description="Track URI for add operations"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Edit a playlist by modifying both local state and Spotify playlist.
    
    This endpoint allows editing of both draft and saved playlists.
    
    Args:
        session_id: Playlist session ID
        edit_type: Type of edit (reorder/remove/add)
        track_id: Track ID for the edit
        new_position: New position for reorder operations
        track_uri: Track URI for add operations
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Updated playlist information
    """
    try:
        # Refresh Spotify token if expired
        current_user = await refresh_spotify_token_if_expired(current_user, db)
        
        # Use the completed playlist editor service
        result = await completed_playlist_editor.edit_playlist(
            session_id=session_id,
            edit_type=edit_type,
            db=db,
            access_token=current_user.access_token,
            user_id=current_user.id,
            track_id=track_id,
            new_position=new_position,
            track_uri=track_uri
        )
        
        return result
    
    except PermissionError as e:
        raise ForbiddenException(str(e))
    except ValueError as e:
        raise ValidationException(str(e))
    except (ForbiddenException, ValidationException):
        raise
    except Exception as e:
        logger.error(f"Error editing playlist: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to edit playlist: {str(e)}")


@router.post("/playlists/{session_id}/save-to-spotify")
async def save_playlist_to_spotify(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Save the draft playlist to Spotify.

    Args:
        session_id: Playlist session ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Playlist creation result
    """
    try:
        # Refresh Spotify token if expired before saving to Spotify
        current_user = await refresh_spotify_token_if_expired(current_user, db)

        # For now, we need to create a workflow manager to get workflow state
        # This is a temporary solution - ideally this logic should be moved to a service
        from ..agents.workflows.workflow_manager import WorkflowConfig

        workflow_config = WorkflowConfig(
            max_retries=3,
            timeout_per_agent=120,
            max_recommendations=25,
            enable_human_loop=True,
            require_approval=True
        )

        # Create minimal workflow manager just to access workflow state
        workflow_manager = WorkflowManager(workflow_config, {}, reccobeat_service.tools)

        # First try to get from workflow manager (Redis/cache)
        state = workflow_manager.get_workflow_state(session_id)

        # If not in cache, load from database
        if not state:
            query = select(Playlist).where(Playlist.session_id == session_id)
            result = await db.execute(query)
            playlist = result.scalar_one_or_none()

            if not playlist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Playlist {session_id} not found"
                )

            # Check if already saved to Spotify
            if playlist.spotify_playlist_id:
                return {
                    "session_id": session_id,
                    "already_saved": True,
                    "playlist_id": playlist.spotify_playlist_id,
                    "playlist_name": playlist.playlist_data.get("name") if playlist.playlist_data else None,
                    "spotify_url": playlist.playlist_data.get("spotify_url") if playlist.playlist_data else None,
                    "message": "Playlist already saved to Spotify"
                }

            # Reconstruct state from database
            recommendations = [
                TrackRecommendation(
                    track_id=rec["track_id"],
                    track_name=rec["track_name"],
                    artists=rec["artists"],
                    spotify_uri=rec.get("spotify_uri"),
                    confidence_score=rec.get("confidence_score", 0.5),
                    reasoning=rec.get("reasoning", ""),
                    source=rec.get("source", "unknown")
                )
                for rec in (playlist.recommendations_data or [])
            ]

            state = AgentState(
                session_id=session_id,
                user_id=str(current_user.id),
                mood_prompt=playlist.mood_prompt,
                spotify_user_id=current_user.spotify_id,
                status=RecommendationStatus.COMPLETED,
                current_step="completed",
                recommendations=recommendations,
                mood_analysis=playlist.mood_analysis_data,
                metadata={"spotify_access_token": current_user.access_token}
            )
        else:
            # In-memory state exists
            if not state.is_complete():
                raise ValidationException("Workflow is not complete yet")

            if state.playlist_id:
                # Already saved
                return {
                    "session_id": session_id,
                    "already_saved": True,
                    "playlist_id": state.playlist_id,
                    "playlist_name": state.playlist_name,
                    "spotify_url": state.metadata.get("playlist_url"),
                    "message": "Playlist already saved to Spotify"
                }

            # Add access token to metadata for playlist creation
            state.metadata["spotify_access_token"] = current_user.access_token

        # Create playlist on Spotify using the playlist creation service
        state = await playlist_creation_service.create_playlist(state)

        if not state.playlist_id:
            raise InternalServerError("Failed to create playlist on Spotify")

        # Mark as saved
        state.metadata["playlist_saved_to_spotify"] = True
        state.metadata["spotify_save_timestamp"] = datetime.utcnow().isoformat()

        # Update database with final playlist info
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist_db = result.scalar_one_or_none()

        if playlist_db:
            playlist_db.spotify_playlist_id = state.playlist_id
            playlist_db.status = PlaylistStatus.COMPLETED
            playlist_db.playlist_data = {
                "name": state.playlist_name,
                "spotify_url": state.metadata.get("playlist_url"),
                "spotify_uri": state.metadata.get("playlist_uri")
            }
            await db.commit()
            logger.info(f"Updated playlist {playlist_db.id} with Spotify info")

        return {
            "session_id": session_id,
            "playlist_id": state.playlist_id,
            "playlist_name": state.playlist_name,
            "spotify_url": state.metadata.get("playlist_url"),
            "spotify_uri": state.metadata.get("playlist_uri"),
            "tracks_added": len(state.recommendations),
            "message": "Playlist successfully saved to Spotify!"
        }

    except (ValidationException, InternalServerError):
        raise
    except Exception as e:
        logger.error(f"Error saving playlist to Spotify: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to save playlist: {str(e)}")

