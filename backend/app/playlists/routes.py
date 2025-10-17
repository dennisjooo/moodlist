"""Playlist CRUD routes for managing user playlists."""

import structlog
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from app.core.exceptions import NotFoundException
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
    InternalServerError
)
from ..dependencies import get_playlist_service
from ..services.playlist_service import PlaylistService
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
    playlist_service: PlaylistService = Depends(get_playlist_service),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    status: Optional[str] = Query(default=None, description="Filter by status (pending, completed, failed)")
):
    """Get all playlists created by the current user.

    Args:
        current_user: Authenticated user
        playlist_service: Playlist service
        limit: Maximum number of playlists to return
        offset: Number of playlists to skip
        status: Optional status filter

    Returns:
        List of user's playlists with pagination info
    """
    try:
        # Get playlists from repository with filtering
        playlists = await playlist_service.playlist_repository.get_by_user_id_with_filters(
            user_id=current_user.id,
            status=status,
            skip=offset,
            limit=limit
        )

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

        # Get total count for pagination
        total_count = await playlist_service.playlist_repository.count_user_playlists_with_filters(
            user_id=current_user.id,
            status=status
        )

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
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Get a specific playlist by ID.

    Args:
        playlist_id: Playlist database ID
        current_user: Authenticated user
        playlist_service: Playlist service

    Returns:
        Playlist details
    """
    try:
        return await playlist_service.get_playlist_by_id(playlist_id, current_user.id)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist {playlist_id}: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get playlist: {str(e)}")


@router.get("/playlists/session/{session_id}")
async def get_playlist_by_session(
    session_id: str,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Get a playlist by its session ID.

    Args:
        session_id: Workflow session UUID
        current_user: Authenticated user
        playlist_service: Playlist service

    Returns:
        Playlist details
    """
    try:
        # Get playlist entity from repository
        playlist = await playlist_service.playlist_repository.get_by_session_id_for_user(
            session_id, current_user.id
        )

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
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Soft delete a playlist.

    Args:
        playlist_id: Playlist database ID
        current_user: Authenticated user
        playlist_service: Playlist service

    Returns:
        Success message
    """
    try:
        # Check if playlist exists and belongs to user
        playlist = await playlist_service.playlist_repository.get_by_id_for_user(
            playlist_id, current_user.id
        )

        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))

        # Soft delete the playlist
        deleted = await playlist_service.playlist_repository.soft_delete(playlist_id)

        if not deleted:
            raise NotFoundException("Playlist", str(playlist_id))

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
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Get user's playlist statistics.

    Args:
        current_user: Authenticated user
        playlist_service: Playlist service

    Returns:
        Playlist statistics
    """
    try:
        # Get statistics from repository
        stats = await playlist_service.playlist_repository.get_user_playlist_stats(current_user.id)

        return {
            **stats,
            "user_id": current_user.id
        }

    except Exception as e:
        logger.error(f"Error getting playlist stats: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get playlist stats: {str(e)}")


@router.get("/stats/public")
async def get_public_stats(
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Get public platform statistics (no authentication required).

    Args:
        playlist_service: Playlist service

    Returns:
        Public platform statistics including total users and playlists count
    """
    try:
        # Get public statistics from repository
        return await playlist_service.playlist_repository.get_public_playlist_stats()

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
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Save the draft playlist to Spotify.

    Args:
        session_id: Playlist session ID
        current_user: Authenticated user
        playlist_service: Playlist service

    Returns:
        Playlist creation result
    """
    try:
        # Refresh Spotify token if expired before saving to Spotify
        # TODO: Move this to a service layer method
        from app.core.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        db = await anext(get_db())
        try:
            current_user = await refresh_spotify_token_if_expired(current_user, db)
        finally:
            await db.close()

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
            playlist = await playlist_service.playlist_repository.get_by_session_id_for_update(session_id)

            if not playlist:
                raise NotFoundException("Playlist", session_id)

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
        state.metadata["spotify_save_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Update database with final playlist info
        updated = await playlist_service.playlist_repository.update_playlist_spotify_info(
            session_id=session_id,
            spotify_playlist_id=state.playlist_id,
            playlist_name=state.playlist_name,
            spotify_url=state.metadata.get("playlist_url"),
            spotify_uri=state.metadata.get("playlist_uri")
        )

        if updated:
            logger.info(f"Updated playlist with session_id {session_id} with Spotify info")

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


@router.post("/playlists/{session_id}/sync-from-spotify")
async def sync_playlist_from_spotify(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Sync playlist tracks from Spotify to local database.

    Args:
        session_id: Playlist session ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Sync results
    """
    try:
        # Refresh Spotify token if expired
        current_user = await refresh_spotify_token_if_expired(current_user, db)

        # Import dependencies
        from app.clients.spotify_client import SpotifyAPIClient
        from app.repositories.playlist_repository import PlaylistRepository
        from .services.playlist_sync_service import PlaylistSyncService

        # Initialize services
        spotify_client = SpotifyAPIClient()
        playlist_repository = PlaylistRepository(db)
        sync_service = PlaylistSyncService(spotify_client, playlist_repository)

        # Perform sync
        result = await sync_service.sync_from_spotify(
            session_id,
            current_user.access_token,
            current_user.id
        )

        return result

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error syncing playlist from Spotify: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to sync playlist: {str(e)}")

