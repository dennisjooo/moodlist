"""Base agent class for the mood-based playlist generation system."""

import asyncio
import structlog
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..states.agent_state import AgentState


logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        name: str,
        description: str,
        llm: Optional[BaseLanguageModel] = None,
        tools: Optional[List[BaseTool]] = None,
        verbose: bool = False
    ):
        """Initialize the base agent.

        Args:
            name: Agent name for identification
            description: Agent description for context
            llm: Language model for decision making
            tools: Available tools for the agent
            verbose: Whether to enable verbose logging
        """
        self.name = name
        self.description = description
        self.llm = llm
        self.tools = tools or []
        self.verbose = verbose

        # Agent state and memory
        self.state: Optional[AgentState] = None
        self.memory: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()

        # Performance tracking
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0

        logger.info(f"Initialized agent: {name}")

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's primary function.

        Args:
            state: Current agent state

        Returns:
            Updated agent state
        """
        pass

    async def pre_execute(self, state: AgentState) -> AgentState:
        """Pre-execution hook for setup and validation.

        Args:
            state: Current agent state

        Returns:
            Potentially modified state
        """
        if self.verbose:
            logger.info(f"Agent {self.name} starting execution")

        # Update execution tracking
        self.execution_count += 1
        state.metadata["agent_name"] = self.name
        state.metadata["execution_start"] = datetime.utcnow().isoformat()

        return state

    async def post_execute(self, state: AgentState) -> AgentState:
        """Post-execution hook for cleanup and state updates.

        Args:
            state: Current agent state

        Returns:
            Final updated state
        """
        # Update execution tracking
        start_time = state.metadata.get("execution_start")
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                execution_time = (datetime.utcnow() - start_dt.replace(tzinfo=None)).total_seconds()
                self.total_execution_time += execution_time
                state.metadata["execution_time"] = execution_time
            except (ValueError, TypeError):
                logger.warning("Could not calculate execution time")

        # Store in memory if significant
        if self._should_store_in_memory(state):
            self.memory.append({
                "timestamp": datetime.utcnow().isoformat(),
                "state_summary": self._get_state_summary(state),
                "metadata": state.metadata.copy()
            })

            # Keep memory manageable
            if len(self.memory) > 100:
                self.memory = self.memory[-50:]  # Keep last 50 items

        if self.verbose:
            logger.info(f"Agent {self.name} completed execution in {state.metadata.get('execution_time', 'unknown')}s")

        return state

    def _should_store_in_memory(self, state: AgentState) -> bool:
        """Determine if this state should be stored in memory.

        Args:
            state: Current agent state

        Returns:
            Whether to store in memory
        """
        # Store if there are recommendations or errors
        return (
            len(state.recommendations) > 0 or
            state.error_message is not None or
            state.current_step in ["completed", "failed"]
        )

    def _get_state_summary(self, state: AgentState) -> Dict[str, Any]:
        """Get a summary of the current state for memory.

        Args:
            state: Current agent state

        Returns:
            State summary dictionary
        """
        return {
            "step": state.current_step,
            "mood_prompt": state.mood_prompt[:50] + "..." if len(state.mood_prompt) > 50 else state.mood_prompt,
            "recommendation_count": len(state.recommendations),
            "has_error": state.error_message is not None,
            "playlist_id": state.playlist_id
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics.

        Returns:
            Performance statistics dictionary
        """
        avg_execution_time = (
            self.total_execution_time / self.execution_count
            if self.execution_count > 0 else 0
        )

        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.execution_count, 1),
            "memory_size": len(self.memory),
            "created_at": self.created_at.isoformat()
        }

    def reset_memory(self):
        """Reset the agent's memory."""
        self.memory.clear()
        logger.info(f"Reset memory for agent: {self.name}")

    def add_tool(self, tool: BaseTool):
        """Add a tool to the agent.

        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        logger.info(f"Added tool {tool.name} to agent {self.name}")

    def remove_tool(self, tool_name: str):
        """Remove a tool from the agent.

        Args:
            tool_name: Name of tool to remove
        """
        self.tools = [t for t in self.tools if t.name != tool_name]
        logger.info(f"Removed tool {tool_name} from agent {self.name}")

    async def run_with_error_handling(self, state: AgentState) -> AgentState:
        """Run the agent with comprehensive error handling.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with error handling
        """
        try:
            # Pre-execution
            state = await self.pre_execute(state)

            # Main execution
            state = await self.execute(state)

            # Post-execution
            state = await self.post_execute(state)

        except Exception as e:
            logger.error(f"Error in agent {self.name}: {str(e)}", exc_info=True)
            self.error_count += 1

            # Update state with error
            state.error_message = str(e)
            state.current_step = "failed"
            state.metadata["error_timestamp"] = datetime.utcnow().isoformat()
            state.metadata["error_type"] = type(e).__name__

            # Ensure post-execution still runs for cleanup
            state = await self.post_execute(state)

        return state