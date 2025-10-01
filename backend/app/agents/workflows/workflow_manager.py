"""Workflow manager for coordinating agentic recommendation process."""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.agent_tools import AgentTools


logger = logging.getLogger(__name__)


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

        # Performance tracking
        self.workflow_count = 0
        self.success_count = 0
        self.failure_count = 0

        logger.info("Initialized WorkflowManager with {} agents".format(len(agents)))

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

        # Start workflow execution
        asyncio.create_task(self._execute_workflow(session_id))

        return session_id

    async def _execute_workflow(self, session_id: str):
        """Execute the complete workflow for a session.

        Args:
            session_id: Workflow session ID
        """
        if session_id not in self.active_workflows:
            logger.error(f"Workflow {session_id} not found")
            return

        state = self.active_workflows[session_id]
        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing workflow {session_id}")

            # Execute workflow steps
            state = await self._execute_mood_analysis(state)
            state = await self._execute_seed_gathering(state)
            state = await self._execute_recommendation_generation(state)
            
            # Mark as completed after recommendations are ready
            state.status = RecommendationStatus.COMPLETED
            state.current_step = "recommendations_ready"
            state.metadata["playlist_saved_to_spotify"] = False
            self.success_count += 1

        except Exception as e:
            logger.error(f"Workflow {session_id} failed: {str(e)}", exc_info=True)
            state.set_error(str(e))
            self.failure_count += 1

        finally:
            # Move to completed workflows
            completion_time = datetime.utcnow()
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

    def cancel_workflow(self, session_id: str) -> bool:
        """Cancel an active workflow.

        Args:
            session_id: Workflow session ID

        Returns:
            Whether cancellation was successful
        """
        if session_id in self.active_workflows:
            state = self.active_workflows.pop(session_id)
            state.set_error("Workflow cancelled by user")
            self.completed_workflows[session_id] = state
            logger.info(f"Cancelled workflow {session_id}")
            return True
        return False

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
        cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)

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