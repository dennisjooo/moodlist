"""FastAPI routes for the agentic recommendation system."""

import logging
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from langchain_openai import ChatOpenAI

from ...core.config import settings
from ...core.database import get_db
from ...auth.dependencies import require_auth
from ...models.user import User
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
playlist_editor = PlaylistEditorAgent(verbose=True)
playlist_creator = PlaylistCreatorAgent(spotify_service, llm, verbose=True)

# Create orchestrator agent (must be created after other agents)
orchestrator = OrchestratorAgent(
    mood_analyzer=mood_analyzer,
    recommendation_generator=recommendation_generator,
    seed_gatherer=seed_gatherer,
    llm=llm,
    max_iterations=2,
    cohesion_threshold=0.75,
    verbose=True
)

# Create workflow manager
workflow_config = WorkflowConfig(
    max_retries=3,
    timeout_per_agent=60,
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
    background_tasks: BackgroundTasks = None
):
    """Start a new mood-based recommendation workflow.

    Args:
        mood_prompt: User's mood description
        current_user: Authenticated user (from session)
        background_tasks: FastAPI background tasks

    Returns:
        Workflow session information
    """
    try:
        logger.info(f"Starting recommendation workflow for user {current_user.id}, mood: {mood_prompt}")

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
async def get_workflow_status(session_id: str):
    """Get the current status of a recommendation workflow.

    Args:
        session_id: Workflow session ID

    Returns:
        Current workflow status
    """
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )

        return {
            "session_id": session_id,
            "status": state.status.value,
            "current_step": state.current_step,
            "mood_prompt": state.mood_prompt,
            "recommendation_count": len(state.recommendations),
            "has_playlist": state.playlist_id is not None,
            "awaiting_input": state.awaiting_user_input,
            "error": state.error_message,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get("/recommendations/{session_id}/results")
async def get_workflow_results(session_id: str):
    """Get the final results of a completed recommendation workflow.

    Args:
        session_id: Workflow session ID

    Returns:
        Complete workflow results
    """
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )

        if not state.is_complete():
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Workflow {session_id} is still in progress"
            )

        # Return complete results
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
            ],
            "playlist": {
                "id": state.playlist_id,
                "name": state.playlist_name,
                "spotify_url": state.metadata.get("playlist_url"),
                "spotify_uri": state.metadata.get("playlist_uri")
            } if state.playlist_id else None,
            "metadata": state.metadata,
            "created_at": state.created_at.isoformat(),
            "completed_at": state.updated_at.isoformat()
        }

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
    current_user: User = Depends(require_auth)
):
    """Save the draft playlist to Spotify.

    Args:
        session_id: Workflow session ID
        current_user: Authenticated user

    Returns:
        Playlist creation result
    """
    try:
        state = workflow_manager.get_workflow_state(session_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found"
            )

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


@router.delete("/recommendations/{session_id}")
async def cancel_workflow(session_id: str):
    """Cancel an active recommendation workflow.

    Args:
        session_id: Workflow session ID

    Returns:
        Cancellation confirmation
    """
    try:
        cancelled = workflow_manager.cancel_workflow(session_id)

        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {session_id} not found or already complete"
            )

        return {
            "session_id": session_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


@router.get("/system/status")
async def get_system_status():
    """Get the current status of the agentic system.

    Returns:
        System status information
    """
    try:
        # Get workflow manager stats
        workflow_stats = workflow_manager.get_performance_stats()

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