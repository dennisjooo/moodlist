"""Workflow manager for coordinating agentic recommendation process."""

import asyncio
import structlog
import uuid
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from ...clients.spotify_client import SpotifyAPIClient
from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.agent_tools import AgentTools


logger = structlog.get_logger(__name__)

# Type alias for state change callback
StateChangeCallback = Callable[[str, AgentState], Awaitable[None]]


class WorkflowConfig:
    """Configuration for the recommendation workflow."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_per_agent: int = 60,
        max_recommendations: int = 30,
        enable_human_loop: bool = True,
        require_approval: bool = False
    ):
        """Initialize workflow configuration.

        Args:
            max_retries: Maximum retries per agent
            timeout_per_agent: Timeout per agent in seconds
            max_recommendations: Maximum number of recommendations
            enable_human_loop: Whether to enable human-in-the-loop
            require_approval: Whether to require final approval
        """
        self.max_retries = max_retries
        self.timeout_per_agent = timeout_per_agent
        self.max_recommendations = max_recommendations
        self.enable_human_loop = enable_human_loop
        self.require_approval = require_approval


class WorkflowManager:
    """Manages the complete recommendation workflow."""

    def __init__(
        self,
        config: WorkflowConfig,
        agents: Dict[str, BaseAgent],
        tools: AgentTools
    ):
        """Initialize the workflow manager.

        Args:
            config: Workflow configuration
            agents: Dictionary of available agents
            tools: Available tools
        """
        self.config = config
        self.agents = agents
        self.tools = tools

        # Workflow state
        self.active_workflows: Dict[str, AgentState] = {}
        self.completed_workflows: Dict[str, AgentState] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}  # Track running tasks

        # State change notifications for SSE
        self.state_change_callbacks: Dict[str, List[StateChangeCallback]] = {}

        # Performance tracking
        self.workflow_count = 0
        self.success_count = 0
        self.failure_count = 0

        logger.info("Initialized WorkflowManager with {} agents".format(len(agents)))

    def subscribe_to_state_changes(self, session_id: str, callback: StateChangeCallback):
        """Subscribe to state changes for a specific workflow session.
        
        Args:
            session_id: Workflow session ID to subscribe to
            callback: Async callback function to call when state changes
        """
        if session_id not in self.state_change_callbacks:
            self.state_change_callbacks[session_id] = []
        self.state_change_callbacks[session_id].append(callback)
        logger.debug(f"Added state change callback for session {session_id}")

    def unsubscribe_from_state_changes(self, session_id: str, callback: StateChangeCallback):
        """Unsubscribe from state changes for a specific workflow session.
        
        Args:
            session_id: Workflow session ID to unsubscribe from
            callback: Callback function to remove
        """
        if session_id in self.state_change_callbacks:
            try:
                self.state_change_callbacks[session_id].remove(callback)
                if not self.state_change_callbacks[session_id]:
                    del self.state_change_callbacks[session_id]
                logger.debug(f"Removed state change callback for session {session_id}")
            except ValueError:
                pass

    async def _notify_state_change(self, session_id: str, state: AgentState):
        """Notify all subscribers of a state change.
        
        Args:
            session_id: Workflow session ID
            state: Updated workflow state
        """
        if session_id in self.state_change_callbacks:
            callbacks = self.state_change_callbacks[session_id].copy()
            for callback in callbacks:
                try:
                    await callback(session_id, state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {str(e)}", exc_info=True)

    async def _update_state(self, session_id: str, state: AgentState):
        """Update workflow state and notify subscribers.
        
        Args:
            session_id: Workflow session ID
            state: Updated workflow state
        """
        self.active_workflows[session_id] = state
        await self._update_playlist_db(session_id, state)
        await self._notify_state_change(session_id, state)

    async def _refresh_spotify_token_if_needed(self, state: AgentState) -> AgentState:
        """Refresh the Spotify access token if needed during workflow execution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with refreshed token if needed
        """
        try:
            # Check if we have a user_id and can refresh the token
            if not state.user_id:
                logger.warning("No user_id in state, cannot refresh token")
                return state
            
            # Get user from database to check token expiry and refresh
            from ...core.database import async_session_factory
            from ...models.user import User
            
            async with async_session_factory() as db:
                result = await db.execute(
                    select(User).where(User.id == int(state.user_id))
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User {state.user_id} not found for token refresh")
                    return state
                
                # Check if token is expired or will expire soon (within 5 minutes)
                now = datetime.now(timezone.utc)
                token_expires_at = user.token_expires_at
                
                # Handle both timezone-aware and naive datetimes
                if token_expires_at.tzinfo is None:
                    token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)
                
                # If token is still valid (more than 5 minutes remaining), no need to refresh
                if token_expires_at > now + timedelta(minutes=5):
                    return state
                
                logger.info(f"Refreshing expired Spotify token for user {user.id}")
                
                # Refresh the token
                spotify_client = SpotifyAPIClient()
                token_data = await spotify_client.refresh_token(user.refresh_token)
                
                # Update user's tokens in database
                user.access_token = token_data["access_token"]
                if "refresh_token" in token_data:
                    user.refresh_token = token_data["refresh_token"]
                
                # Update expiration time
                expires_in = token_data.get("expires_in", 3600)
                user.token_expires_at = datetime.now(timezone.utc).replace(microsecond=0) + \
                                       timedelta(seconds=expires_in)
                
                await db.commit()
                
                # Update the state with new token
                state.metadata["spotify_access_token"] = user.access_token
                
                logger.info(f"Successfully refreshed Spotify token for user {user.id}, expires at {user.token_expires_at}")
                
        except Exception as e:
            logger.error(f"Failed to refresh Spotify token: {str(e)}", exc_info=True)
        
        return state

    async def _update_playlist_db(self, session_id: str, state: AgentState) -> None:
        """Update the playlist database with workflow state.

        Args:
            session_id: Workflow session ID
            state: Current workflow state
        """
        try:
            from ...core.database import async_session_factory
            from ...models.playlist import Playlist
            
            async with async_session_factory() as db:
                # Find the playlist by session_id
                result = await db.execute(
                    select(Playlist).where(Playlist.session_id == session_id)
                )
                playlist = result.scalar_one_or_none()
                
                if playlist:
                    # Update status
                    playlist.status = state.status.value
                    
                    # Update mood analysis if available
                    if state.mood_analysis:
                        playlist.mood_analysis_data = state.mood_analysis
                    
                    # Update recommendations if available
                    if state.recommendations:
                        playlist.recommendations_data = [
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
                        ]
                        playlist.track_count = len(state.recommendations)
                    
                    # Update playlist metadata if created
                    if state.playlist_id:
                        playlist.spotify_playlist_id = state.playlist_id
                        playlist.playlist_data = {
                            "name": state.playlist_name,
                            "spotify_url": state.metadata.get("playlist_url"),
                            "spotify_uri": state.metadata.get("playlist_uri")
                        }
                    
                    # Update error if present
                    if state.error_message:
                        playlist.error_message = state.error_message
                    
                    await db.commit()
                    logger.debug(f"Updated playlist DB for session {session_id}")
                else:
                    logger.warning(f"Playlist not found for session {session_id}")
                    
        except Exception as e:
            logger.error(f"Failed to update playlist DB for session {session_id}: {str(e)}", exc_info=True)

    async def start_workflow(
        self,
        mood_prompt: str,
        user_id: str,
        spotify_user_id: Optional[str] = None
    ) -> str:
        """Start a new recommendation workflow.

        Args:
            mood_prompt: User's mood description
            user_id: User identifier
            spotify_user_id: Optional Spotify user ID

        Returns:
            Workflow session ID
        """
        session_id = str(uuid.uuid4())

        # Create initial state
        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            mood_prompt=mood_prompt,
            spotify_user_id=spotify_user_id,
            current_step="initializing",
            status=RecommendationStatus.PENDING
        )

        # Store workflow
        self.active_workflows[session_id] = state
        self.workflow_count += 1

        logger.info(f"Started workflow {session_id} for mood: {mood_prompt[:50]}...")

        # Start workflow execution and track the task
        task = asyncio.create_task(self._execute_workflow(session_id))
        self.active_tasks[session_id] = task

        return session_id

    def cancel_workflow(self, session_id: str) -> bool:
        """Cancel an active workflow.

        Args:
            session_id: Workflow session ID to cancel

        Returns:
            True if workflow was cancelled, False if not found or already completed
        """
        if session_id in self.active_workflows:
            state = self.active_workflows[session_id]
            state.status = RecommendationStatus.FAILED
            state.error_message = "Workflow cancelled by user"
            state.current_step = "cancelled"
            
            # Cancel the asyncio task if it exists
            if session_id in self.active_tasks:
                task = self.active_tasks[session_id]
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled asyncio task for workflow {session_id}")
                del self.active_tasks[session_id]
            
            # Move to completed workflows
            self.completed_workflows[session_id] = self.active_workflows.pop(session_id)
            self.failure_count += 1
            
            logger.info(f"Workflow {session_id} cancelled by user")
            return True
        
        logger.warning(f"Attempted to cancel non-existent or completed workflow {session_id}")
        return False

    async def _execute_workflow(self, session_id: str):
        """Execute the complete workflow for a session.

        Args:
            session_id: Workflow session ID
        """
        if session_id not in self.active_workflows:
            logger.error(f"Workflow {session_id} not found")
            return

        state = self.active_workflows[session_id]
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Executing workflow {session_id}")

            # Execute workflow steps
            state = await self._execute_mood_analysis(state)
            await self._update_state(session_id, state)
            
            # Execute orchestration (handles seed gathering, recommendations, and quality improvement)
            state = await self._execute_orchestration(state)
            await self._update_state(session_id, state)
            
            # Mark as completed after recommendations are ready
            state.status = RecommendationStatus.COMPLETED
            state.current_step = "recommendations_ready"
            state.metadata["playlist_saved_to_spotify"] = False
            await self._update_state(session_id, state)
            self.success_count += 1
            
            # Dump the state to a file
            with open(f"logs/workflow_{session_id}.json", "w") as f:
                import json
                
                def serialize_datetime(obj):
                    """Recursively serialize datetime objects to ISO format strings."""
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: serialize_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [serialize_datetime(item) for item in obj]
                    elif isinstance(obj, tuple):
                        return tuple(serialize_datetime(item) for item in obj)
                    elif hasattr(obj, '__dict__'):
                        return serialize_datetime(obj.__dict__)
                    else:
                        return obj
                
                state_dict = state.model_dump()
                serialized_state = serialize_datetime(state_dict)
                f.write(json.dumps(serialized_state, indent=4, default=str))

        except asyncio.CancelledError:
            logger.info(f"Workflow {session_id} was cancelled")
            state.status = RecommendationStatus.FAILED
            state.error_message = "Workflow cancelled by user"
            self.failure_count += 1
            raise  # Re-raise to properly handle cancellation

        except Exception as e:
            logger.error(f"Workflow {session_id} failed: {str(e)}", exc_info=True)
            state.set_error(str(e))
            self.failure_count += 1

        finally:
            # Clean up task reference
            if session_id in self.active_tasks:
                del self.active_tasks[session_id]
            
            # Move to completed workflows if still in active
            if session_id in self.active_workflows:
                completion_time = datetime.now(timezone.utc)
                state.metadata["completion_time"] = completion_time.isoformat()
                state.metadata["total_duration"] = (completion_time - start_time).total_seconds()

                self.completed_workflows[session_id] = self.active_workflows.pop(session_id)

                logger.info(f"Workflow {session_id} completed in {state.metadata['total_duration']:.2f}s")

    async def _execute_mood_analysis(self, state: AgentState) -> AgentState:
        """Execute mood analysis step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "analyzing_mood"
        state.status = RecommendationStatus.ANALYZING_MOOD

        mood_agent = self.agents.get("mood_analyzer")
        if not mood_agent:
            raise ValueError("Mood analyzer agent not available")

        return await mood_agent.run_with_error_handling(state)

    async def _execute_seed_gathering(self, state: AgentState) -> AgentState:
        """Execute seed gathering step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "gathering_seeds"
        state.status = RecommendationStatus.GATHERING_SEEDS

        seed_agent = self.agents.get("seed_gatherer")
        if not seed_agent:
            raise ValueError("Seed gatherer agent not available")

        return await seed_agent.run_with_error_handling(state)

    async def _execute_recommendation_generation(self, state: AgentState) -> AgentState:
        """Execute recommendation generation step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "generating_recommendations"
        state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS

        recommendation_agent = self.agents.get("recommendation_generator")
        if not recommendation_agent:
            raise ValueError("Recommendation generator agent not available")

        return await recommendation_agent.run_with_error_handling(state)

    async def _execute_orchestration(self, state: AgentState) -> AgentState:
        """Execute orchestration for quality evaluation and improvement.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        # Refresh token before orchestration (which includes seed gathering and artist discovery)
        state = await self._refresh_spotify_token_if_needed(state)
        
        state.current_step = "evaluating_quality"
        state.status = RecommendationStatus.EVALUATING_QUALITY

        orchestrator = self.agents.get("orchestrator")
        if not orchestrator:
            logger.warning("Orchestrator agent not available, skipping quality optimization")
            return state

        # Set progress callback for real-time SSE updates during orchestration
        async def notify_progress(updated_state: AgentState):
            """Callback to notify SSE clients of state changes."""
            await self._notify_state_change(state.session_id, updated_state)
        
        orchestrator._progress_callback = notify_progress
        return await orchestrator.run_with_error_handling(state)

    async def _execute_human_loop(self, state: AgentState) -> AgentState:
        """Execute human-in-the-loop step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "awaiting_user_input"
        state.status = RecommendationStatus.AWAITING_USER_INPUT
        state.awaiting_user_input = True

        # Wait for user input (in real implementation, this would be event-driven)
        # For now, we'll simulate with a timeout or auto-approve
        logger.info(f"Workflow {state.session_id} awaiting user input")

        # In a real implementation, this would wait for user interaction
        # For now, we'll auto-approve after a brief pause
        await asyncio.sleep(0.1)

        state.awaiting_user_input = False
        return state

    async def _execute_playlist_creation(self, state: AgentState) -> AgentState:
        """Execute playlist creation step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "creating_playlist"
        state.status = RecommendationStatus.CREATING_PLAYLIST

        playlist_agent = self.agents.get("playlist_creator")
        if not playlist_agent:
            raise ValueError("Playlist creator agent not available")

        return await playlist_agent.run_with_error_handling(state)

    def get_workflow_state(self, session_id: str) -> Optional[AgentState]:
        """Get the current state of a workflow.

        Args:
            session_id: Workflow session ID

        Returns:
            Current state or None if not found
        """
        return (
            self.active_workflows.get(session_id) or
            self.completed_workflows.get(session_id)
        )

    def get_workflow_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a workflow.

        Args:
            session_id: Workflow session ID

        Returns:
            Workflow summary or None if not found
        """
        state = self.get_workflow_state(session_id)
        if not state:
            return None

        return {
            "session_id": session_id,
            "status": state.status.value,
            "current_step": state.current_step,
            "mood_prompt": state.mood_prompt,
            "recommendation_count": len(state.recommendations),
            "has_playlist": state.playlist_id is not None,
            "created_at": state.created_at.isoformat(),
            "is_active": session_id in self.active_workflows
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get workflow manager performance statistics.

        Returns:
            Performance statistics
        """
        total_workflows = self.workflow_count
        success_rate = self.success_count / max(total_workflows, 1)

        return {
            "total_workflows": total_workflows,
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "average_completion_time": self._calculate_average_completion_time()
        }

    def _calculate_average_completion_time(self) -> float:
        """Calculate average completion time for completed workflows.

        Returns:
            Average completion time in seconds
        """
        if not self.completed_workflows:
            return 0.0

        total_time = sum(
            state.metadata.get("total_duration", 0)
            for state in self.completed_workflows.values()
        )

        return total_time / len(self.completed_workflows)

    def cleanup_old_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - max_age_hours)

        to_remove = []
        for session_id, state in self.completed_workflows.items():
            if state.created_at < cutoff_time:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.completed_workflows[session_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old workflows")

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows.

        Returns:
            List of workflow summaries
        """
        return [
            self.get_workflow_summary(session_id)
            for session_id in self.active_workflows.keys()
        ]

    def list_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent completed workflows.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List of recent workflow summaries
        """
        recent_workflows = list(self.completed_workflows.values())
        recent_workflows.sort(key=lambda x: x.created_at, reverse=True)

        return [
            workflow.get_summary()
            for workflow in recent_workflows[:limit]
        ]