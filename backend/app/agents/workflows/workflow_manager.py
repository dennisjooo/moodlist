"""Workflow manager for coordinating agentic recommendation process."""

import asyncio
import json
import structlog
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.agent_tools import AgentTools
from .workflow_state_manager import WorkflowStateManager, StateChangeCallback
from .workflow_executor import WorkflowExecutor


logger = structlog.get_logger(__name__)


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
    """Manages the complete recommendation workflow.
    
    Refactored to use specialized managers for better separation of concerns.
    """

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

        # Initialize specialized managers
        self.state_manager = WorkflowStateManager()
        self.executor = WorkflowExecutor(agents)

        # Track running tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}

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
        self.state_manager.subscribe_to_state_changes(session_id, callback)

    def unsubscribe_from_state_changes(self, session_id: str, callback: StateChangeCallback):
        """Unsubscribe from state changes for a specific workflow session.
        
        Args:
            session_id: Workflow session ID to unsubscribe from
            callback: Callback function to remove
        """
        self.state_manager.unsubscribe_from_state_changes(session_id, callback)

    async def _update_state(self, session_id: str, state: AgentState):
        """Update workflow state and notify subscribers.
        
        Args:
            session_id: Workflow session ID
            state: Updated workflow state
        """
        await self.state_manager.update_state(session_id, state)


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
        self.state_manager.active_workflows[session_id] = state
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
        if session_id in self.state_manager.active_workflows:
            state = self.state_manager.active_workflows[session_id]
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
            self.state_manager.move_to_completed(session_id, state)
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
        if session_id not in self.state_manager.active_workflows:
            logger.error(f"Workflow {session_id} not found")
            return

        state = self.state_manager.active_workflows[session_id]
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Executing workflow {session_id}")

            # Execute workflow steps in the updated order
            # STEP 1: Analyze user intent FIRST
            state = await self.executor.execute_intent_analysis(state)
            await self._update_state(session_id, state)
            # Check for cancellation
            if state.status == RecommendationStatus.FAILED and state.error_message == "Workflow cancelled by user":
                return

            # STEP 2: Analyze mood (now focused on audio features only)
            state = await self.executor.execute_mood_analysis(state)
            await self._update_state(session_id, state)
            # Check for cancellation
            if state.status == RecommendationStatus.FAILED and state.error_message == "Workflow cancelled by user":
                return

            # STEP 3-5: Execute orchestration (handles seed gathering, recommendations, and quality improvement)
            async def notify_progress(updated_state: AgentState):
                """Callback to notify SSE clients of state changes."""
                await self.state_manager.notify_state_change(state.session_id, updated_state)

            state = await self.executor.execute_orchestration(state, progress_callback=notify_progress)
            await self._update_state(session_id, state)
            # Check for cancellation
            if state.status == RecommendationStatus.FAILED and state.error_message == "Workflow cancelled by user":
                return

            # STEP 6: Order playlist tracks for optimal energy flow
            state = await self.executor.execute_playlist_ordering(state)
            await self._update_state(session_id, state)
            # Check for cancellation
            if state.status == RecommendationStatus.FAILED and state.error_message == "Workflow cancelled by user":
                return
            
            # Mark as completed after recommendations are ready
            state.status = RecommendationStatus.COMPLETED
            state.current_step = "recommendations_ready"
            state.metadata["playlist_saved_to_spotify"] = False
            await self._update_state(session_id, state)
            self.success_count += 1
            
            # Dump the state to a file
            self._save_workflow_state_to_file(session_id, state)

        except asyncio.CancelledError:
            logger.info(f"Workflow {session_id} was cancelled")
            state.status = RecommendationStatus.FAILED
            state.error_message = "Workflow cancelled by user"
            self.failure_count += 1
            raise

        except Exception as e:
            logger.error(f"Workflow {session_id} failed: {str(e)}", exc_info=True)
            state.set_error(str(e))
            self.failure_count += 1

        finally:
            # Clean up task reference
            if session_id in self.active_tasks:
                del self.active_tasks[session_id]
            
            # Move to completed workflows if still in active
            if session_id in self.state_manager.active_workflows:
                completion_time = datetime.now(timezone.utc)
                state.metadata["completion_time"] = completion_time.isoformat()
                state.metadata["total_duration"] = (completion_time - start_time).total_seconds()

                self.state_manager.move_to_completed(session_id, state)

                logger.info(f"Workflow {session_id} completed in {state.metadata['total_duration']:.2f}s")

    def _save_workflow_state_to_file(self, session_id: str, state: AgentState):
        """Save workflow state to a JSON file for debugging.

        Args:
            session_id: Workflow session ID
            state: Workflow state to save
        """
        try:
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

            with open(f"logs/workflow_{session_id}.json", "w") as f:
                state_dict = state.model_dump()
                serialized_state = serialize_datetime(state_dict)
                f.write(json.dumps(serialized_state, indent=4, default=str))
        except Exception as e:
            logger.error(f"Failed to save workflow state to file: {e}")


    def get_workflow_state(self, session_id: str) -> Optional[AgentState]:
        """Get the current state of a workflow.

        Args:
            session_id: Workflow session ID

        Returns:
            Current state or None if not found
        """
        return (
            self.state_manager.active_workflows.get(session_id) or
            self.state_manager.completed_workflows.get(session_id)
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
            "is_active": session_id in self.state_manager.active_workflows
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
            "active_workflows": len(self.state_manager.active_workflows),
            "completed_workflows": len(self.state_manager.completed_workflows),
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
        if not self.state_manager.completed_workflows:
            return 0.0

        total_time = sum(
            state.metadata.get("total_duration", 0)
            for state in self.state_manager.completed_workflows.values()
        )

        return total_time / len(self.state_manager.completed_workflows)

    def cleanup_old_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        self.state_manager.cleanup_old_workflows(max_age_hours)

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows.

        Returns:
            List of workflow summaries
        """
        return [
            self.get_workflow_summary(session_id)
            for session_id in self.state_manager.active_workflows.keys()
        ]

    def list_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent completed workflows.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List of recent workflow summaries
        """
        recent_workflows = list(self.state_manager.completed_workflows.values())
        recent_workflows.sort(key=lambda x: x.created_at, reverse=True)

        return [
            workflow.get_summary()
            for workflow in recent_workflows[:limit]
        ]
