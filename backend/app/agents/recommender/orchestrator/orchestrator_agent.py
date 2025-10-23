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
            state = await self.perform_final_processing(state, quality_evaluation)

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
        await self._notify_progress(state)
        
        # Pass progress callback to seed gatherer
        if hasattr(self, '_progress_callback'):
            self.seed_gatherer._progress_callback = self._progress_callback
        state = await self.seed_gatherer.run_with_error_handling(state)

        logger.info("Initial recommendation generation...")
        state.current_step = "generating_recommendations"
        state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS
        await self._notify_progress(state)
        
        # Pass progress callback to recommendation generator
        if hasattr(self, '_progress_callback'):
            self.recommendation_generator._progress_callback = self._progress_callback
        state = await self.recommendation_generator.run_with_error_handling(state)

        return state

    async def perform_iterative_improvement(self, state: AgentState) -> Dict[str, Any]:
        """Perform iterative improvement loop."""
        quality_evaluation = None

        for iteration in range(self.max_iterations):
            state.metadata["orchestration_iterations"] = iteration + 1
            state.current_step = f"evaluating_quality_iteration_{iteration + 1}"
            state.status = RecommendationStatus.EVALUATING_QUALITY
            await self._notify_progress(state)

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
            await self._notify_progress(state)

            improvement_strategies = await self.improvement_strategy.decide_improvement_strategy(
                quality_evaluation, state
            )
            logger.info(f"Applying improvement strategies: {improvement_strategies}")

            state = await self.improvement_strategy.apply_improvements(
                improvement_strategies, quality_evaluation, state
            )

            # Small delay between iterations
            await asyncio.sleep(0.1)
            
            # Remove duplicates
            state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)

        return quality_evaluation

    async def perform_final_processing(self, state: AgentState, quality_evaluation: Dict[str, Any]) -> AgentState:
        """Perform final processing and cleanup with outlier filtering."""
        logger.info("Starting final processing and cleanup...")
        
        # Remove duplicates
        state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)
        
        # Run final quality evaluation to get fresh outlier list
        final_evaluation = await self.quality_evaluator.evaluate_playlist_quality(state)
        state.metadata["final_quality_evaluation"] = final_evaluation
        
        # Filter out outliers from final recommendations (but keep protected tracks)
        outlier_ids = set(final_evaluation.get("outlier_tracks", []))
        if outlier_ids:
            original_count = len(state.recommendations)
            filtered_recommendations = []
            protected_kept = 0
            
            for rec in state.recommendations:
                if rec.track_id in outlier_ids:
                    # CRITICAL: Never filter protected tracks (user-mentioned)
                    if rec.protected or rec.user_mentioned:
                        logger.info(
                            f"Keeping outlier because it's protected: {rec.track_name} by {', '.join(rec.artists)}"
                        )
                        filtered_recommendations.append(rec)
                        protected_kept += 1
                    else:
                        logger.info(
                            f"Filtering outlier from final playlist: {rec.track_name} by {', '.join(rec.artists)} "
                            f"(cohesion: {final_evaluation['track_scores'].get(rec.track_id, 0):.2f})"
                        )
                else:
                    filtered_recommendations.append(rec)
            
            state.recommendations = filtered_recommendations
            
            logger.info(
                f"Final outlier filtering: removed {original_count - len(filtered_recommendations)} tracks "
                f"({protected_kept} protected tracks kept despite being outliers)"
            )
            
            # Check if we're below target after filtering - regenerate to meet target
            playlist_target = state.metadata.get("playlist_target", {})
            target_count = playlist_target.get("target_count", 20)
            min_count = playlist_target.get("min_count", 15)

            if len(state.recommendations) < target_count:
                shortfall = target_count - len(state.recommendations)
                logger.warning(
                    f"Below target after filtering ({len(state.recommendations)} < {target_count}). "
                    f"Generating {shortfall} additional recommendations..."
                )

                # Use remaining good tracks as seeds
                if state.recommendations:
                    state.seed_tracks = [rec.track_id for rec in state.recommendations[:5]]

                # Generate enough to reach target (recommendation generator will add to existing)
                # Store current count to know how many were added
                before_count = len(state.recommendations)
                state = await self.recommendation_generator.run_with_error_handling(state)
                added_count = len(state.recommendations) - before_count

                logger.info(f"Added {added_count} tracks, now have {len(state.recommendations)} total")
            elif len(state.recommendations) < min_count:
                # Emergency regeneration if somehow below minimum
                logger.error(f"Critical: Below minimum after filtering ({len(state.recommendations)} < {min_count})")
                if state.recommendations:
                    state.seed_tracks = [rec.track_id for rec in state.recommendations[:5]]
                state = await self.recommendation_generator.run_with_error_handling(state)
        

        # Enforce ratio respecting the target count
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)
        max_count = playlist_target.get("max_count", 30)

        # Use target_count as the limit since we regenerated to meet it
        # But cap at max_count as a safety measure
        final_limit = min(target_count, max_count, len(state.recommendations))

        # Enforce 95:5 ratio (95% artist, 5% RecoBeat) at the target count
        state.recommendations = self.recommendation_processor.enforce_source_ratio(
            recommendations=state.recommendations,
            max_count=final_limit,
            artist_ratio=0.95
        )
        
        # Final state update
        state.current_step = "recommendations_ready"
        
        logger.info(
            f"Final processing complete: {len(state.recommendations)} tracks delivered "
            f"(cohesion: {final_evaluation['cohesion_score']:.2f}, "
            f"overall: {final_evaluation['overall_score']:.2f})"
        )

        return state