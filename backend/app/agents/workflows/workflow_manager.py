"""Workflow manager for coordinating agentic recommendation process."""

import asyncio
import json
import os
import structlog
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ...core.config import settings
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
        # Don't update state if workflow has been cancelled
        # Check both active and completed workflows to handle race conditions
        if self.is_cancelled(session_id):
            logger.debug(f"Skipping state update for cancelled workflow {session_id}")
            return
        
        # Also check the state object directly
        if state.status == RecommendationStatus.CANCELLED:
            logger.debug(f"Skipping state update - state already marked as cancelled for {session_id}")
            return
        
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
            
            # Check if already cancelled or completed
            if state.status == RecommendationStatus.CANCELLED:
                logger.info(f"Workflow {session_id} already cancelled")
                return True
            
            # Update state atomically
            state.status = RecommendationStatus.CANCELLED
            state.error_message = "Workflow cancelled by user"
            state.current_step = "cancelled"
            state.update_timestamp()
            
            # Cancel the asyncio task if it exists
            if session_id in self.active_tasks:
                task = self.active_tasks[session_id]
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled asyncio task for workflow {session_id}")
                del self.active_tasks[session_id]
            
            # Move to completed workflows
            # Note: The route handler will update the database, so we don't need to do it here
            self.state_manager.move_to_completed(session_id, state)
            
            self.failure_count += 1
            
            logger.info(f"Workflow {session_id} cancelled by user")
            return True
        
        # Check if it's in completed workflows but not cancelled
        if session_id in self.state_manager.completed_workflows:
            state = self.state_manager.completed_workflows[session_id]
            if state.status != RecommendationStatus.CANCELLED:
                # Update to cancelled even if already completed
                state.status = RecommendationStatus.CANCELLED
                state.error_message = "Workflow cancelled by user"
                state.current_step = "cancelled"
                state.update_timestamp()
                logger.info(f"Updated completed workflow {session_id} to cancelled status")
                return True
        
        logger.warning(f"Attempted to cancel non-existent workflow {session_id}")
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

        def check_cancellation() -> bool:
            """Check if workflow has been cancelled.
            
            Returns:
                True if cancelled, False otherwise
            """
            if self.is_cancelled(session_id):
                return True
            # Also check the state object directly
            if state.status == RecommendationStatus.CANCELLED:
                return True
            return False

        try:
            logger.info(f"Executing workflow {session_id}")

            # Check cancellation before starting
            if check_cancellation():
                logger.info(f"Workflow {session_id} was cancelled before execution started")
                return

            # Execute workflow steps in the updated order
            # STEP 1: Analyze user intent FIRST
            if check_cancellation():
                return
            state = await self.executor.execute_intent_analysis(state)
            # Only update state if not cancelled
            if not check_cancellation():
                await self._update_state(session_id, state)
            if check_cancellation():
                return

            # STEP 2: Analyze mood (now focused on audio features only)
            if check_cancellation():
                return
            state = await self.executor.execute_mood_analysis(state)
            # Only update state if not cancelled
            if not check_cancellation():
                await self._update_state(session_id, state)
            if check_cancellation():
                return

            # STEP 3-5: Execute orchestration (handles seed gathering, recommendations, and quality improvement)
            async def notify_progress(updated_state: AgentState):
                """Callback to notify SSE clients of state changes."""
                # Don't notify if workflow is cancelled
                if check_cancellation():
                    return
                
                # Get current state to ensure we don't send backwards updates
                current_state = self.get_workflow_state(state.session_id)
                if current_state:
                    # Only send if this is forward progress (newer status or step)
                    from ..states.agent_state import RecommendationStatus
                    
                    # Define status progression order
                    status_order = {
                        RecommendationStatus.PENDING: 0,
                        RecommendationStatus.ANALYZING_MOOD: 1,
                        RecommendationStatus.GATHERING_SEEDS: 2,
                        RecommendationStatus.GENERATING_RECOMMENDATIONS: 3,
                        RecommendationStatus.EVALUATING_QUALITY: 4,
                        RecommendationStatus.OPTIMIZING_RECOMMENDATIONS: 5,
                        RecommendationStatus.COMPLETED: 6,
                        RecommendationStatus.FAILED: 6,
                        RecommendationStatus.CANCELLED: 6,
                    }
                    
                    current_status_order = status_order.get(current_state.status, -1)
                    updated_status_order = status_order.get(updated_state.status, -1)
                    
                    # Allow same status (sub-steps within a stage) or forward progress
                    if updated_status_order >= current_status_order:
                        await self.state_manager.notify_state_change(state.session_id, updated_state)
                    else:
                        logger.debug(
                            f"Skipping backwards progress notification: {current_state.status.value} -> {updated_state.status.value}",
                            session_id=state.session_id
                        )
                else:
                    # No current state, safe to send
                    await self.state_manager.notify_state_change(state.session_id, updated_state)

            if check_cancellation():
                return
            state = await self.executor.execute_orchestration(state, progress_callback=notify_progress)
            # Only update state if not cancelled
            if not check_cancellation():
                await self._update_state(session_id, state)
            if check_cancellation():
                return

            # STEP 6: Order playlist tracks for optimal energy flow
            if check_cancellation():
                return
            state = await self.executor.execute_playlist_ordering(state)
            # Only update state if not cancelled
            if not check_cancellation():
                await self._update_state(session_id, state)
            if check_cancellation():
                return
            
            # Mark as completed after recommendations are ready
            if not check_cancellation():
                state.status = RecommendationStatus.COMPLETED
                state.current_step = "recommendations_ready"
                state.metadata["playlist_saved_to_spotify"] = False
                await self._update_state(session_id, state)
                self.success_count += 1
                
                # Dump the state to a file if DEBUG is enabled
                if settings.DEBUG:
                    self._save_workflow_state_to_file(session_id, state)

        except asyncio.CancelledError:
            logger.info(f"Workflow {session_id} was cancelled")
            # Ensure state reflects cancellation
            if state.status != RecommendationStatus.CANCELLED:
                state.status = RecommendationStatus.CANCELLED
                state.error_message = "Workflow cancelled by user"
                state.current_step = "cancelled"
                state.update_timestamp()
                await self._update_state(session_id, state)
            self.failure_count += 1
            raise

        except Exception as e:
            logger.error(f"Workflow {session_id} failed: {str(e)}", exc_info=True)
            # Don't overwrite cancellation status with error
            if state.status != RecommendationStatus.CANCELLED:
                state.set_error(str(e))
            self.failure_count += 1

        finally:
            # Clean up task reference
            if session_id in self.active_tasks:
                del self.active_tasks[session_id]
            
            # Move to completed workflows if still in active
            # But preserve cancelled status if it was set
            if session_id in self.state_manager.active_workflows:
                # Check if workflow was cancelled - if so, ensure status is preserved
                is_cancelled = self.is_cancelled(session_id) or state.status == RecommendationStatus.CANCELLED
                
                if is_cancelled and state.status != RecommendationStatus.CANCELLED:
                    # Restore cancelled status if it was lost
                    state.status = RecommendationStatus.CANCELLED
                    state.error_message = "Workflow cancelled by user"
                    state.current_step = "cancelled"
                    state.update_timestamp()
                
                completion_time = datetime.now(timezone.utc)
                state.metadata["completion_time"] = completion_time.isoformat()
                state.metadata["total_duration"] = (completion_time - start_time).total_seconds()

                # Send final notification before moving to completed
                # This ensures subscribers get the final state
                await self.state_manager.notify_state_change(session_id, state)
                
                self.state_manager.move_to_completed(session_id, state)

                status_msg = "cancelled" if is_cancelled else "completed"
                logger.info(f"Workflow {session_id} {status_msg} in {state.metadata['total_duration']:.2f}s")

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
            
            # Check if logs directory exists
            if not os.path.exists("logs"):
                os.makedirs("logs")

            # Create timestamp for filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"logs/workflow_{timestamp}_{session_id}.json"
            with open(filename, "w") as f:
                state_dict = state.model_dump()
                serialized_state = serialize_datetime(state_dict)
                f.write(json.dumps(serialized_state, indent=4, default=str))
        except Exception as e:
            logger.error(f"Failed to save workflow state to file: {e}")


    def is_cancelled(self, session_id: str) -> bool:
        """Check if a workflow has been cancelled.

        Args:
            session_id: Workflow session ID

        Returns:
            True if workflow is cancelled, False otherwise
        """
        state = self.get_workflow_state(session_id)
        return state is not None and state.status == RecommendationStatus.CANCELLED

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

    async def graceful_shutdown(self, timeout: int = 300):
        """Wait for active workflows to complete before shutdown.

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)
        """
        if not self.active_tasks:
            logger.info("No active workflows, proceeding with shutdown")
            return

        active_count = len(self.active_tasks)
        logger.info(
            f"Graceful shutdown initiated: waiting for {active_count} active workflow(s) to complete",
            active_workflows=list(self.active_tasks.keys()),
            timeout=timeout
        )

        try:
            # Wait for all active tasks with timeout
            await asyncio.wait_for(
                asyncio.gather(*self.active_tasks.values(), return_exceptions=True),
                timeout=timeout
            )
            logger.info(f"All {active_count} workflows completed successfully during shutdown")
        except asyncio.TimeoutError:
            remaining = len([t for t in self.active_tasks.values() if not t.done()])
            logger.warning(
                f"Graceful shutdown timeout after {timeout}s: {remaining} workflow(s) still running",
                remaining_workflows=list(self.active_tasks.keys())
            )
            # Cancel remaining tasks
            for session_id, task in list(self.active_tasks.items()):
                if not task.done():
                    logger.info(f"Force-cancelling workflow {session_id} due to shutdown timeout")
                    task.cancel()
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
