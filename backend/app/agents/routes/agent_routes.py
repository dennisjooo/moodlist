"""FastAPI routes for the agentic recommendation system."""

import logging
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db
from ...auth.dependencies import require_auth, refresh_spotify_token_if_expired
from ...models.user import User
from ...models.playlist import Playlist
from ..workflows.workflow_manager import WorkflowManager, WorkflowConfig
from ..tools.reccobeat_service import RecoBeatService
from ..tools.spotify_service import SpotifyService
from ..agents import (
    MoodAnalyzerAgent,
    SeedGathererAgent,
    RecommendationGeneratorAgent,
    PlaylistEditorAgent,
    PlaylistCreatorAgent,
    OrchestratorAgent
)
from ..states.agent_state import  PlaylistEdit


logger = logging.getLogger(__name__)

# Initialize services and agents
reccobeat_service = RecoBeatService()
spotify_service = SpotifyService()

llm = ChatOpenAI(
    model="x-ai/grok-4-fast:free",
    temperature=1,
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

groq_llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    temperature=1,
    base_url="https://api.groq.com/openai/v1",
    api_key="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"
)

cerebras_llm = ChatOpenAI(
    model="gpt-oss-120b",
    temperature=1,
    base_url="https://api.cerebras.ai/v1",
    api_key="csk-8ex8pkwm8wcmx6c2xhmcedv5d3e5fr4ek9jmvtvj9hfw9e53"
)

# Create agents with updated dependencies
mood_analyzer = MoodAnalyzerAgent(llm=cerebras_llm, spotify_service=spotify_service, verbose=True)
seed_gatherer = SeedGathererAgent(
    spotify_service=spotify_service,
    reccobeat_service=reccobeat_service,
    llm=groq_llm,
    verbose=True
)
recommendation_generator = RecommendationGeneratorAgent(
    reccobeat_service,
    spotify_service,
    max_recommendations=25,  # Limit to 25 tracks for focused playlists
    verbose=True
)
playlist_editor = PlaylistEditorAgent(verbose=True)
playlist_creator = PlaylistCreatorAgent(spotify_service, llm, verbose=True)

# Create orchestrator agent (must be created after other agents)
orchestrator = OrchestratorAgent(
    mood_analyzer=mood_analyzer,
    recommendation_generator=recommendation_generator,
    seed_gatherer=seed_gatherer,
    llm=cerebras_llm,
    max_iterations=3,
    cohesion_threshold=0.75,
    verbose=True
)

# Create workflow manager
workflow_config = WorkflowConfig(
    max_retries=3,
    timeout_per_agent=120,
    max_recommendations=25,  # Cap at 25 tracks for manageable playlists
    enable_human_loop=True,
    require_approval=True
)

agents = {
    "mood_analyzer": mood_analyzer,
    "seed_gatherer": seed_gatherer,
    "recommendation_generator": recommendation_generator,
    "playlist_editor": playlist_editor,
    "playlist_creator": playlist_creator,
    "orchestrator": orchestrator
}

workflow_manager = WorkflowManager(workflow_config, agents, reccobeat_service.tools)

router = APIRouter()


@router.post("/recommendations/start")
async def start_recommendation(
    mood_prompt: str = Query(..., description="Mood description for playlist generation"),
    current_user: User = Depends(require_auth),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Start a new mood-based recommendation workflow.

    Args:
        mood_prompt: User's mood description
        current_user: Authenticated user (from session)
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Workflow session information
    """
    try:
        logger.info(f"Starting recommendation workflow for user {current_user.id}, mood: {mood_prompt}")

        # Refresh Spotify token if expired before starting workflow
        current_user = await refresh_spotify_token_if_expired(current_user, db)

        # Start the workflow with authenticated user's information
        session_id = await workflow_manager.start_workflow(
            mood_prompt=mood_prompt,
            user_id=str(current_user.id),
            spotify_user_id=current_user.spotify_id
        )

        # Store access token from authenticated user in workflow state
        state = workflow_manager.get_workflow_state(session_id)
        if state:
            state.metadata["spotify_access_token"] = current_user.access_token

        # Create initial Playlist DB record
        playlist = Playlist(
            user_id=current_user.id,
            session_id=session_id,
            mood_prompt=mood_prompt,
            status="pending"
        )
        db.add(playlist)
        await db.commit()
        await db.refresh(playlist)
        
        logger.info(f"Created playlist record {playlist.id} for session {session_id}")

        return {
            "session_id": session_id,
            "status": "started",
            "mood_prompt": mood_prompt,
            "message": "Recommendation workflow started successfully"
        }

    except Exception as e:
        logger.error(f"Error starting recommendation workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recommendation workflow: {str(e)}"
        )


@router.get("/recommendations/{session_id}/status")
async def get_workflow_status(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get the current status of a recommendation workflow.

    Args:
        session_id: Workflow session ID
        db: Database session

    Returns:
        Current workflow status
    """
    try:
        # First try to get from workflow manager (Redis/cache)
        state = workflow_manager.get_workflow_state(session_id)

        if state:
            return {
                "session_id": session_id,
                "status": state.status.value,
                "current_step": state.current_step,
                "mood_prompt": state.mood_prompt,
                "mood_analysis": state.mood_analysis,
                "recommendation_count": len(state.recommendations),
                "seed_track_count": len(state.seed_tracks),
                "user_top_tracks_count": len(state.user_top_tracks),
                "user_top_artists_count": len(state.user_top_artists),
                "has_playlist": state.playlist_id is not None,
                "awaiting_input": state.awaiting_user_input,
                "error": state.error_message,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat(),
                "metadata": {
                    "iteration": state.metadata.get("iteration"),
                    "cohesion_score": state.metadata.get("cohesion_score"),
                }
            }
        
        # If not in cache, try to get from database
        from sqlalchemy import select
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )
        
        # Return status from database
        recommendation_count = 0
        if playlist.recommendations_data:
            recommendation_count = len(playlist.recommendations_data)
        
        return {
            "session_id": session_id,
            "status": playlist.status,
            "current_step": "completed" if playlist.status == "completed" else playlist.status,
            "mood_prompt": playlist.mood_prompt,
            "mood_analysis": playlist.mood_analysis_data,
            "recommendation_count": recommendation_count,
            "has_playlist": playlist.spotify_playlist_id is not None,
            "awaiting_input": False,  # Persisted workflows are not awaiting input
            "error": playlist.error_message,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.delete("/recommendations/{session_id}")
async def cancel_workflow(session_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel an active workflow.

    Args:
        session_id: Workflow session ID to cancel
        db: Database session

    Returns:
        Cancellation confirmation
    """
    try:
        cancelled = workflow_manager.cancel_workflow(session_id)
        
        # Update playlist status in database to "cancelled"
        from sqlalchemy import select
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if playlist:
            playlist.status = "cancelled"
            playlist.error_message = "Workflow cancelled by user"
            await db.commit()
            logger.info(f"Updated playlist {playlist.id} status to cancelled")
        
        if cancelled or playlist:
            return {
                "session_id": session_id,
                "status": "cancelled",
                "message": "Workflow cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found or already completed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


@router.get("/recommendations/{session_id}/results")
async def get_workflow_results(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get the final results of a completed recommendation workflow.

    Args:
        session_id: Workflow session ID
        db: Database session

    Returns:
        Complete workflow results
    """
    try:
        # Always check database first for persisted playlists
        from sqlalchemy import select
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        # If playlist exists in DB with recommendations, use that (it's the source of truth for edits)
        if playlist and playlist.recommendations_data:
            result = {
                "session_id": session_id,
                "status": playlist.status,
                "mood_prompt": playlist.mood_prompt,
                "mood_analysis": playlist.mood_analysis_data,
                "recommendations": playlist.recommendations_data,
                "playlist": {
                    "id": playlist.spotify_playlist_id,
                    "name": playlist.playlist_data.get("name") if playlist.playlist_data else None,
                    "spotify_url": playlist.playlist_data.get("spotify_url") if playlist.playlist_data else None,
                    "spotify_uri": playlist.playlist_data.get("spotify_uri") if playlist.playlist_data else None
                } if playlist.spotify_playlist_id else None,
                "metadata": {},
                "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
                "completed_at": playlist.updated_at.isoformat() if playlist.updated_at else None
            }
            
            return result
        
        # Fallback to in-memory state for workflows that haven't been persisted yet
        state = workflow_manager.get_workflow_state(session_id)
        if state:
            # Return partial results even if workflow is not complete
            # This allows frontend to show mood analysis early
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
                        "source": rec.source
                    }
                    for rec in state.recommendations
                ] if state.is_complete() or len(state.recommendations) > 0 else [],
                "playlist": {
                    "id": state.playlist_id,
                    "name": state.playlist_name,
                    "spotify_url": state.metadata.get("playlist_url"),
                    "spotify_uri": state.metadata.get("playlist_uri")
                } if state.playlist_id else None,
                "metadata": state.metadata,
                "created_at": state.created_at.isoformat(),
                "completed_at": state.updated_at.isoformat() if state.is_complete() else None
            }
        
        # If we reach here, workflow doesn't exist anywhere
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {session_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow results: {str(e)}"
        )


@router.post("/recommendations/{session_id}/edit")
async def edit_playlist(
    session_id: str,
    edit_type: str = Query(..., description="Type of edit (reorder/remove/add/replace)"),
    track_id: Optional[str] = Query(None, description="Track ID for edit"),
    new_position: Optional[int] = Query(None, description="New position for reorder"),
    reasoning: Optional[str] = Query(None, description="User reasoning for edit")
):
    """Apply an edit to the current playlist recommendations.

    Args:
        session_id: Workflow session ID
        edit_type: Type of edit to apply
        track_id: Track ID for the edit
        new_position: New position for reorder operations
        reasoning: User's reasoning for the edit

    Returns:
        Updated workflow status
    """
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )

        if state.is_complete():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow {session_id} is already complete"
            )

        # Create edit object
        edit = PlaylistEdit(
            edit_type=edit_type,
            track_id=track_id,
            new_position=new_position,
            reasoning=reasoning
        )

        # Validate edit
        if not playlist_editor.validate_edit(edit, state.recommendations):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid edit parameters"
            )

        # Apply edit
        state.add_user_edit(edit)

        # Process the edit
        state = await playlist_editor.run_with_error_handling(state)

        return {
            "session_id": session_id,
            "status": state.status.value,
            "current_step": state.current_step,
            "edit_applied": edit.edit_type,
            "recommendation_count": len(state.recommendations),
            "awaiting_input": state.awaiting_user_input
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying playlist edit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply playlist edit: {str(e)}"
        )


@router.get("/recommendations/{session_id}/playlist")
async def get_playlist_details(session_id: str):
    """Get detailed playlist information for a completed workflow.

    Args:
        session_id: Workflow session ID

    Returns:
        Detailed playlist information
    """
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )

        if not state.is_complete() or not state.playlist_id:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Playlist not ready for workflow {session_id}"
            )

        # Get playlist summary
        playlist_summary = playlist_creator.get_playlist_summary(state)

        # Get detailed track information
        tracks = [
            {
                "position": i,
                "track_id": rec.track_id,
                "track_name": rec.track_name,
                "artists": rec.artists,
                "spotify_uri": rec.spotify_uri,
                "confidence_score": rec.confidence_score,
                "reasoning": rec.reasoning,
                "source": rec.source
            }
            for i, rec in enumerate(state.recommendations)
        ]

        return {
            "session_id": session_id,
            "playlist": playlist_summary,
            "tracks": tracks,
            "mood_analysis": state.mood_analysis,
            "total_tracks": len(tracks),
            "created_at": state.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get playlist details: {str(e)}"
        )


@router.post("/recommendations/{session_id}/save-to-spotify")
async def save_playlist_to_spotify(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Save the draft playlist to Spotify.

    Args:
        session_id: Workflow session ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Playlist creation result
    """
    try:
        # Refresh Spotify token if expired before saving to Spotify
        current_user = await refresh_spotify_token_if_expired(current_user, db)
        
        # First try to get from workflow manager (Redis/cache)
        state = workflow_manager.get_workflow_state(session_id)

        # If not in cache, load from database
        if not state:
            from sqlalchemy import select
            from ..states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
            
            query = select(Playlist).where(Playlist.session_id == session_id)
            result = await db.execute(query)
            playlist = result.scalar_one_or_none()
            
            if not playlist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {session_id} not found"
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workflow is not complete yet"
                )

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

        # Create playlist on Spotify using the playlist creator agent
        if not playlist_creator:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Playlist creator not available"
            )

        state = await playlist_creator.run_with_error_handling(state)

        if not state.playlist_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create playlist on Spotify"
            )

        # Mark as saved
        state.metadata["playlist_saved_to_spotify"] = True
        state.metadata["spotify_save_timestamp"] = datetime.utcnow().isoformat()
        
        # Update database with final playlist info
        from sqlalchemy import select
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist_db = result.scalar_one_or_none()
        
        if playlist_db:
            playlist_db.spotify_playlist_id = state.playlist_id
            playlist_db.status = "completed"
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving playlist to Spotify: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save playlist: {str(e)}"
        )


@router.get("/system/status")
async def get_system_status():
    """Get the current status of the agentic system.

    Returns:
        System status information
    """
    try:
        # Get workflow manager stats
        workflow_stats = await workflow_manager.get_performance_stats()

        # Get agent performance stats
        agent_stats = {}
        for name, agent in agents.items():
            agent_stats[name] = agent.get_performance_stats()

        return {
            "system_status": "operational",
            "workflow_manager": workflow_stats,
            "agents": agent_stats,
            "available_tools": {
                "reccobeat": reccobeat_service.get_available_tools(),
                "spotify": spotify_service.get_available_tools()
            }
        }

    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )


@router.get("/workflows/active")
async def list_active_workflows():
    """List all currently active workflows.

    Returns:
        List of active workflow summaries
    """
    try:
        active_workflows = workflow_manager.list_active_workflows()

        return {
            "active_workflows": active_workflows,
            "total_count": len(active_workflows)
        }

    except Exception as e:
        logger.error(f"Error listing active workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active workflows: {str(e)}"
        )


@router.get("/workflows/recent")
async def list_recent_workflows(limit: int = Query(default=10, le=50)):
    """List recent completed workflows.

    Args:
        limit: Maximum number of workflows to return

    Returns:
        List of recent workflow summaries
    """
    try:
        recent_workflows = workflow_manager.list_recent_workflows(limit)

        return {
            "recent_workflows": recent_workflows,
            "total_count": len(recent_workflows)
        }

    except Exception as e:
        logger.error(f"Error listing recent workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list recent workflows: {str(e)}"
        )


@router.post("/recommendations/{session_id}/edit-completed")
async def edit_completed_playlist(
    session_id: str,
    edit_type: str = Query(..., description="Type of edit (reorder/remove/add)"),
    track_id: Optional[str] = Query(None, description="Track ID for edit"),
    new_position: Optional[int] = Query(None, description="New position for reorder"),
    track_uri: Optional[str] = Query(None, description="Track URI for add operations"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Edit a completed/saved playlist by modifying both local state and Spotify playlist.
    
    This endpoint bypasses the is_complete() check and directly modifies the Spotify playlist.
    
    Args:
        session_id: Workflow session ID
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
        
        # Load playlist from database
        from sqlalchemy import select
        query = select(Playlist).where(Playlist.session_id == session_id)
        result = await db.execute(query)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Playlist with session {session_id} not found"
            )
        
        # Validate user owns this playlist
        if playlist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this playlist"
            )
        
        # Check if playlist has been saved to Spotify
        is_saved_to_spotify = bool(playlist.spotify_playlist_id)
        
        # Get current recommendations
        recommendations = playlist.recommendations_data or []
        
        # Apply edit to local recommendations
        if edit_type == "remove":
            if not track_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="track_id is required for remove operation"
                )
            
            # Find and remove track
            track_to_remove = None
            for i, rec in enumerate(recommendations):
                if rec.get("track_id") == track_id:
                    track_to_remove = recommendations.pop(i)
                    break
            
            if not track_to_remove:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Track {track_id} not found in playlist"
                )
            
            # Remove from Spotify if playlist is saved
            if is_saved_to_spotify:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.delete(
                        f"https://api.spotify.com/v1/playlists/{playlist.spotify_playlist_id}/tracks",
                        headers={"Authorization": f"Bearer {current_user.access_token}"},
                        json={"tracks": [{"uri": track_to_remove.get("spotify_uri")}]}
                    )
                    response.raise_for_status()
                
                logger.info(f"Removed track {track_id} from Spotify playlist {playlist.spotify_playlist_id}")
            else:
                logger.info(f"Removed track {track_id} from draft playlist (not yet in Spotify)")
        
        elif edit_type == "reorder":
            if track_id is None or new_position is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="track_id and new_position are required for reorder operation"
                )
            
            # Find track index
            old_index = None
            for i, rec in enumerate(recommendations):
                if rec.get("track_id") == track_id:
                    old_index = i
                    break
            
            if old_index is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Track {track_id} not found in playlist"
                )
            
            # Reorder in local list
            track = recommendations.pop(old_index)
            recommendations.insert(new_position, track)
            
            # Reorder in Spotify if playlist is saved
            if is_saved_to_spotify:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Spotify uses insert_before, so if moving down, add 1
                    insert_before = new_position if old_index > new_position else new_position + 1
                    response = await client.put(
                        f"https://api.spotify.com/v1/playlists/{playlist.spotify_playlist_id}/tracks",
                        headers={"Authorization": f"Bearer {current_user.access_token}"},
                        json={
                            "range_start": old_index,
                            "insert_before": insert_before,
                            "range_length": 1
                        }
                    )
                    response.raise_for_status()
                
                logger.info(f"Reordered track {track_id} from position {old_index} to {new_position} in Spotify")
            else:
                logger.info(f"Reordered track {track_id} from position {old_index} to {new_position} in draft")
        
        elif edit_type == "add":
            if not track_uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="track_uri is required for add operation"
                )
            
            # Get track details from Spotify
            import httpx
            async with httpx.AsyncClient() as client:
                # Extract track ID from URI (format: spotify:track:ID)
                track_id_from_uri = track_uri.split(":")[-1]
                
                # Get track details
                response = await client.get(
                    f"https://api.spotify.com/v1/tracks/{track_id_from_uri}",
                    headers={"Authorization": f"Bearer {current_user.access_token}"}
                )
                response.raise_for_status()
                track_data = response.json()
                
                # Add to local recommendations
                new_track = {
                    "track_id": track_data["id"],
                    "track_name": track_data["name"],
                    "artists": [artist["name"] for artist in track_data["artists"]],
                    "spotify_uri": track_data["uri"],
                    "confidence_score": 0.5,
                    "reasoning": "Added by user",
                    "source": "user_added"
                }
                
                # Add to position or end of list
                if new_position is not None:
                    recommendations.insert(new_position, new_track)
                else:
                    recommendations.append(new_track)
                
                # Add to Spotify if playlist is saved
                if is_saved_to_spotify:
                    response = await client.post(
                        f"https://api.spotify.com/v1/playlists/{playlist.spotify_playlist_id}/tracks",
                        headers={"Authorization": f"Bearer {current_user.access_token}"},
                        json={
                            "uris": [track_uri],
                            "position": new_position
                        } if new_position is not None else {"uris": [track_uri]}
                    )
                    response.raise_for_status()
                    logger.info(f"Added track {track_uri} to Spotify playlist {playlist.spotify_playlist_id}")
                else:
                    logger.info(f"Added track {track_uri} to draft playlist (not yet in Spotify)")
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid edit_type: {edit_type}. Must be one of: reorder, remove, add"
            )
        
        # Update database with modified recommendations
        # Force SQLAlchemy to detect the change by using flag_modified
        from sqlalchemy.orm.attributes import flag_modified
        playlist.recommendations_data = recommendations
        flag_modified(playlist, "recommendations_data")
        playlist.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(playlist)
        
        # Also update in-memory state if it exists
        state = workflow_manager.get_workflow_state(session_id)
        if state:
            # Update the in-memory recommendations to match database
            from ..states.agent_state import TrackRecommendation
            state.recommendations = [
                TrackRecommendation(
                    track_id=rec["track_id"],
                    track_name=rec["track_name"],
                    artists=rec["artists"],
                    spotify_uri=rec.get("spotify_uri"),
                    confidence_score=rec.get("confidence_score", 0.5),
                    reasoning=rec.get("reasoning", ""),
                    source=rec.get("source", "unknown")
                )
                for rec in recommendations
            ]
            logger.info(f"Updated in-memory state for session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "success",
            "edit_type": edit_type,
            "recommendation_count": len(recommendations),
            "message": f"Successfully applied {edit_type} edit to playlist"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing completed playlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to edit playlist: {str(e)}"
        )

