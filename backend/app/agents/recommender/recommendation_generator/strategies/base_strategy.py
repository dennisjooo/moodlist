"""Base class for recommendation generation strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ....states.agent_state import AgentState


class RecommendationStrategy(ABC):
    """Abstract base class for recommendation generation strategies."""

    def __init__(self, name: str):
        """Initialize the strategy.

        Args:
            name: Name identifier for the strategy
        """
        self.name = name

    @abstractmethod
    async def generate_recommendations(
        self,
        state: AgentState,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate recommendations using this strategy.

        Args:
            state: Current agent state
            target_count: Target number of recommendations to generate

        Returns:
            List of recommendation data dictionaries
        """
        pass

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about this strategy.

        Returns:
            Dictionary with strategy metadata
        """
        return {
            "name": self.name,
            "description": self.__class__.__doc__ or f"{self.name} strategy"
        }
