"""Orchestrator agent for evaluating and improving playlist quality."""

import asyncio
import structlog
from typing import Optional, Dict, Any

from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from .quality_evaluator import QualityEvaluator
from .improvement_strategy import ImprovementStrategy
from .recommendation_processor import RecommendationProcessor

logger = structlog.get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """Agent for orchestrating quality evaluation and iterative improvement of playlists."""

    def __init__(
        self,
        mood_analyzer: BaseAgent,
        recommendation_generator: BaseAgent,
        seed_gatherer: BaseAgent,
        llm: Optional[BaseLanguageModel] = None,
        max_iterations: int = 3,
        cohesion_threshold: float = 0.65,
        verbose: bool = False
    ):
        """Initialize the orchestrator agent.

        Args:
            mood_analyzer: MoodAnalyzerAgent instance for re-analysis if needed
            recommendation_generator: RecommendationGeneratorAgent for generating more tracks
            seed_gatherer: SeedGathererAgent for re-seeding if needed
            llm: Language model for decision making
            max_iterations: Maximum improvement iterations before accepting results
            cohesion_threshold: Minimum cohesion score (0-1) to accept playlist (default 0.65)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="orchestrator",
            description="Orchestrates quality evaluation and iterative improvement of playlist recommendations",
            llm=llm,
            verbose=verbose
        )

        self.mood_analyzer = mood_analyzer
        self.recommendation_generator = recommendation_generator
        self.seed_gatherer = seed_gatherer
        self.max_iterations = max_iterations
        self.cohesion_threshold = cohesion_threshold

        # Initialize component modules
        self.quality_evaluator = QualityEvaluator(
            llm=llm,
            cohesion_threshold=cohesion_threshold
        )
        self.improvement_strategy = ImprovementStrategy(
            recommendation_generator=recommendation_generator,
            llm=llm,
            cohesion_threshold=cohesion_threshold
        )
        self.recommendation_processor = RecommendationProcessor()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute orchestration with seed gathering, recommendations, and iterative improvement.

        Args:
            state: Current agent state after mood analysis

        Returns:
            Updated agent state with optimized recommendations
        """
        try:
            logger.info(f"Starting orchestration for session {state.session_id}")

            # Initialize orchestration metadata
            self.initialize_metadata(state)

            # Initial seed gathering and recommendation generation
            state = await self.perform_initial_generation(state)

            # Iterative improvement loop
            quality_evaluation = await self.perform_iterative_improvement(state)

            # Final processing and cleanup
            state = self.perform_final_processing(state, quality_evaluation)

            logger.info(
                f"Orchestration completed with {len(state.recommendations)} unique recommendations "
                f"after {state.metadata['orchestration_iterations']} iteration(s)"
            )

        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}", exc_info=True)
            state.set_error(f"Orchestration failed: {str(e)}")

        return state

    def initialize_metadata(self, state: AgentState) -> None:
        """Initialize orchestration metadata."""
        if "orchestration_iterations" not in state.metadata:
            state.metadata["orchestration_iterations"] = 0
        if "quality_scores" not in state.metadata:
            state.metadata["quality_scores"] = []
        if "improvement_actions" not in state.metadata:
            state.metadata["improvement_actions"] = []

    async def perform_initial_generation(self, state: AgentState) -> AgentState:
        """Perform initial seed gathering and recommendation generation."""
        logger.info("Initial seed gathering...")
        state.current_step = "gathering_seeds"
        state.status = RecommendationStatus.GATHERING_SEEDS
        state = await self.seed_gatherer.run_with_error_handling(state)

        logger.info("Initial recommendation generation...")
        state.current_step = "generating_recommendations"
        state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS
        state = await self.recommendation_generator.run_with_error_handling(state)

        return state

    async def perform_iterative_improvement(self, state: AgentState) -> Dict[str, Any]:
        """Perform iterative improvement loop."""
        quality_evaluation = None

        for iteration in range(self.max_iterations):
            state.metadata["orchestration_iterations"] = iteration + 1
            state.current_step = f"evaluating_quality_iteration_{iteration + 1}"
            state.status = RecommendationStatus.EVALUATING_QUALITY

            # Evaluate current playlist quality
            quality_evaluation = await self.quality_evaluator.evaluate_playlist_quality(state)
            state.metadata["quality_scores"].append(quality_evaluation)

            logger.info(
                f"Iteration {iteration + 1}: Overall score={quality_evaluation['overall_score']:.2f}, "
                f"Cohesion={quality_evaluation['cohesion_score']:.2f}, "
                f"Count={quality_evaluation['recommendations_count']}"
            )

            # Check if quality meets threshold
            if quality_evaluation["meets_threshold"]:
                logger.info(f"Quality threshold met after {iteration + 1} iteration(s)")
                state.current_step = "recommendations_ready"
                break

            # Apply improvement strategies
            state.current_step = f"optimizing_recommendations_iteration_{iteration + 1}"
            state.status = RecommendationStatus.OPTIMIZING_RECOMMENDATIONS

            improvement_strategies = await self.improvement_strategy.decide_improvement_strategy(
                quality_evaluation, state
            )
            logger.info(f"Applying improvement strategies: {improvement_strategies}")

            state = await self.improvement_strategy.apply_improvements(
                improvement_strategies, quality_evaluation, state
            )

            # Small delay between iterations
            await asyncio.sleep(0.1)

        return quality_evaluation

    def perform_final_processing(self, state: AgentState, quality_evaluation: Dict[str, Any]) -> AgentState:
        """Perform final processing and cleanup."""
        # Final state update
        state.current_step = "recommendations_ready"
        state.metadata["final_quality_evaluation"] = quality_evaluation

        # Remove duplicates
        state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)

        # Cap recommendations at max_count to respect target plan
        playlist_target = state.metadata.get("playlist_target", {})
        max_count = playlist_target.get("max_count", 30)

        # Enforce 95:5 ratio (95% artist, 5% RecoBeat) even after iterations
        state.recommendations = self.recommendation_processor.enforce_source_ratio(
            recommendations=state.recommendations,
            max_count=max_count,
            artist_ratio=0.95
        )

        return state