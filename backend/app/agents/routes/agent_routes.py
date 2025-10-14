"""FastAPI routes for the agentic recommendation system."""

import json
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
from ..recommender import (
    MoodAnalyzerAgent,
    SeedGathererAgent,
    RecommendationGeneratorAgent,
    OrchestratorAgent
)


logger = logging.getLogger(__name__)

# Initialize services and agents
reccobeat_service = RecoBeatService()
spotify_service = SpotifyService()

llm = ChatOpenAI(
    model="moonshotai/kimi-k2:free",
    temperature=1,
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
)

groq_llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    temperature=1,
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY
)

cerebras_llm = ChatOpenAI(
    model="gpt-oss-120b",
    temperature=1,
    base_url="https://api.cerebras.ai/v1",
    api_key=settings.CEREBRAS_API_KEY
)

# Create agents with updated dependencies
mood_analyzer = MoodAnalyzerAgent(llm=llm, spotify_service=spotify_service, verbose=True)
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
            mood_prompt=mood_prompt.strip(),
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

