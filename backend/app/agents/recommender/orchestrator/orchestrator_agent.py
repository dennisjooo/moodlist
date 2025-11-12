"""Orchestrator agent for evaluating and improving playlist quality."""

import asyncio
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ...tools.spotify_service import SpotifyService
from ..recommendation_generator.handlers.track_enrichment import TrackEnrichmentService
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
        max_iterations: int = 2,
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
        
        # Initialize track enrichment service
        spotify_service = SpotifyService()
        self.track_enrichment_service = TrackEnrichmentService(spotify_service)

    async def execute(self, state: AgentState) -> AgentState:
        """Execute orchestration with seed gathering, recommendations, and iterative improvement.

        Args:
            state: Current agent state after mood analysis

        Returns:
            Updated agent state with optimized recommendations
        """
        # Initialize timing tracking
        orchestration_timings = {}
        
        try:
            logger.info(f"Starting orchestration for session {state.session_id}")

            # Initialize orchestration metadata
            self.initialize_metadata(state)

            # Initial seed gathering and recommendation generation
            step_start = datetime.now(timezone.utc)
            state = await self.perform_initial_generation(state)
            orchestration_timings["initial_generation"] = (datetime.now(timezone.utc) - step_start).total_seconds()

            # Iterative improvement loop
            step_start = datetime.now(timezone.utc)
            quality_evaluation = await self.perform_iterative_improvement(state)
            orchestration_timings["iterative_improvement"] = (datetime.now(timezone.utc) - step_start).total_seconds()

            # Final processing and cleanup
            step_start = datetime.now(timezone.utc)
            state = await self.perform_final_processing(state, quality_evaluation)
            orchestration_timings["final_processing"] = (datetime.now(timezone.utc) - step_start).total_seconds()

            # Store orchestration timings in state metadata
            state.metadata["orchestration_timings"] = orchestration_timings
            
            # Enhance iterative_improvement timing with breakdown if available
            if "iterative_improvement_timings" in state.metadata:
                iterative_breakdown = state.metadata["iterative_improvement_timings"]
                orchestration_timings["iterative_improvement"] = {
                    "total": orchestration_timings["iterative_improvement"],
                    "breakdown": iterative_breakdown
                }
                # Update the stored timings with the enhanced structure
                state.metadata["orchestration_timings"] = orchestration_timings

            logger.info(
                f"Orchestration completed with {len(state.recommendations)} unique recommendations "
                f"after {state.metadata['orchestration_iterations']} iteration(s)"
            )

        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}", exc_info=True)
            state.set_error(f"Orchestration failed: {str(e)}")
            # Store partial timings even on error
            if orchestration_timings:
                state.metadata["orchestration_timings"] = orchestration_timings

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
        """Perform iterative improvement loop with convergence detection."""
        quality_evaluation = None
        previous_score = 0.0
        convergence_threshold = 0.03  # Must improve by at least 3% to continue (increased from 2% for faster convergence)
        stalled_iterations = 0
        max_stalled = 1  # Stop after 1 iteration with no meaningful improvement (reduced from 2 for faster convergence)

        # Initialize timing tracking for iterative improvement breakdown
        iterative_timings = {
            "quality_evaluation": 0.0,
            "improvement_strategies": 0.0
        }

        for iteration in range(self.max_iterations):
            # Check for cancellation before each iteration
            if state.status == RecommendationStatus.CANCELLED:
                logger.info(f"Orchestration cancelled during iteration {iteration + 1}")
                break
            
            state.metadata["orchestration_iterations"] = iteration + 1
            
            # Evaluate quality and check for convergence
            step_start = datetime.now(timezone.utc)
            quality_evaluation = await self.evaluate_quality_with_convergence(
                state, iteration, previous_score, convergence_threshold,
                stalled_iterations, max_stalled
            )
            iterative_timings["quality_evaluation"] += (datetime.now(timezone.utc) - step_start).total_seconds()
            
            # Check for cancellation after evaluation
            if state.status == RecommendationStatus.CANCELLED:
                logger.info(f"Orchestration cancelled after quality evaluation in iteration {iteration + 1}")
                break
            
            if quality_evaluation is None:
                # Converged or threshold met
                break
                
            # Check if quality meets threshold
            if quality_evaluation["meets_threshold"]:
                logger.info(f"✓ Quality threshold met after {iteration + 1} iteration(s)")
                state.current_step = "recommendations_ready"
                break

            # Apply improvement strategies
            previous_score = quality_evaluation['overall_score']
            step_start = datetime.now(timezone.utc)
            state = await self.apply_improvement_strategies(state, iteration, quality_evaluation)
            iterative_timings["improvement_strategies"] += (datetime.now(timezone.utc) - step_start).total_seconds()
            
            # Check for cancellation after applying improvements
            if state.status == RecommendationStatus.CANCELLED:
                logger.info(f"Orchestration cancelled after applying improvements in iteration {iteration + 1}")
                break

            # Small delay between iterations
            await asyncio.sleep(0.1)

        # Store iterative improvement timings in state metadata
        state.metadata["iterative_improvement_timings"] = iterative_timings

        return quality_evaluation

    async def evaluate_quality_with_convergence(
        self,
        state: AgentState,
        iteration: int,
        previous_score: float,
        convergence_threshold: float,
        stalled_iterations: int,
        max_stalled: int
    ) -> Optional[Dict[str, Any]]:
        """Evaluate playlist quality and check for convergence."""
        state.current_step = f"evaluating_quality_iteration_{iteration + 1}"
        state.status = RecommendationStatus.EVALUATING_QUALITY
        await self._notify_progress(state)

        # Evaluate current playlist quality
        quality_evaluation = await self.quality_evaluator.evaluate_playlist_quality(state)
        state.metadata["quality_scores"].append(quality_evaluation)

        current_score = quality_evaluation['overall_score']
        
        logger.info(
            f"Iteration {iteration + 1}: Overall score={current_score:.2f}, "
            f"Cohesion={quality_evaluation['cohesion_score']:.2f}, "
            f"Count={quality_evaluation['recommendations_count']}"
        )

        # Check for convergence (after first iteration)
        new_stalled_iterations = stalled_iterations
        if iteration > 0:
            improvement = current_score - previous_score
            if improvement < convergence_threshold:
                new_stalled_iterations += 1
                logger.info(
                    f"⚠ Iteration {iteration + 1} stalled: "
                    f"improvement {improvement:.3f} < threshold {convergence_threshold} "
                    f"({new_stalled_iterations}/{max_stalled} stalled iterations)"
                )
            else:
                new_stalled_iterations = 0  # Reset if improvement is significant
                logger.info(f"✓ Meaningful improvement: +{improvement:.3f}")

        # Stop if converged (no improvement for multiple iterations)
        if new_stalled_iterations >= max_stalled:
            logger.info(
                f"✓ Convergence detected after {iteration + 1} iterations "
                f"(score stalled at {current_score:.2f}). Stopping early."
            )
            state.current_step = "recommendations_converged"
            return None

        return quality_evaluation

    async def apply_improvement_strategies(
        self,
        state: AgentState,
        iteration: int,
        quality_evaluation: Dict[str, Any]
    ) -> AgentState:
        """Apply improvement strategies to enhance playlist quality."""
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
        
        return state

    async def perform_final_processing(self, state: AgentState, quality_evaluation: Dict[str, Any]) -> AgentState:
        """Perform final processing and cleanup with outlier filtering."""
        logger.info("Starting final processing and cleanup...")
        
        # Remove duplicates and enrich tracks
        state = await self.handle_duplicates_and_enrichment(state)
        
        # Filter outliers with protection logic
        state = await self.filter_outliers_with_protection(state)
        
        # Enforce playlist targets and source ratios
        state = await self.enforce_playlist_targets(state)
        state = await self.enforce_source_ratio(state)
        
        # Final state update
        state.current_step = "recommendations_ready"
        
        logger.info(
            f"Final processing complete: {len(state.recommendations)} tracks delivered"
        )

        return state

    async def handle_duplicates_and_enrichment(self, state: AgentState) -> AgentState:
        """Remove duplicates and enrich tracks with Spotify data."""
        # Remove duplicates
        state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)
        
        # Enrich tracks with missing Spotify URIs
        state = await self.enrich_tracks_with_spotify_data(state)
        
        return state

    async def filter_outliers_with_protection(self, state: AgentState) -> AgentState:
        """Filter outliers while protecting user-mentioned tracks."""
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
                    if rec.protected or rec.user_mentioned or rec.user_mentioned_artist:
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
        
        return state

    async def enforce_playlist_targets(self, state: AgentState) -> AgentState:
        """Enforce playlist target counts and regenerate if needed."""
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
        
        return state

    async def enforce_source_ratio(self, state: AgentState) -> AgentState:
        """Enforce source ratio and final count limits."""
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
        
        final_evaluation = state.metadata.get("final_quality_evaluation", {})
        logger.info(
            f"Final processing complete: {len(state.recommendations)} tracks delivered "
            f"(cohesion: {final_evaluation.get('cohesion_score', 0):.2f}, "
            f"overall: {final_evaluation.get('overall_score', 0):.2f})"
        )
        
        return state

    async def enrich_tracks_with_spotify_data(self, state: AgentState) -> AgentState:
        """Enrich recommendations with missing Spotify URIs and artist data."""
        if not state.recommendations:
            return state

        try:
            logger.info("Enriching tracks with missing Spotify data...")

            # Validate enrichment requirements
            validation_result = self.validate_enrichment_requirements(state)
            if not validation_result["can_proceed"]:
                return state
                
            access_token = validation_result["access_token"]
            tracks_needing_enrichment = validation_result["tracks_needing_enrichment"]

            # Process track enrichment
            state = await self.process_track_enrichment(state, access_token, tracks_needing_enrichment)

        except Exception as e:
            logger.error(f"Error enriching tracks: {e}", exc_info=True)
            # Don't fail the workflow if enrichment fails
            state.metadata["track_enrichment_error"] = str(e)

        return state

    def validate_enrichment_requirements(self, state: AgentState) -> Dict[str, Any]:
        """Validate if track enrichment can proceed."""
        # Get Spotify access token
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.warning("No Spotify access token available for enrichment")
            return {"can_proceed": False, "access_token": None, "tracks_needing_enrichment": 0}

        # Count tracks that need enrichment
        tracks_needing_enrichment = sum(
            1 for rec in state.recommendations
            if not rec.spotify_uri or
               rec.spotify_uri == "null" or
               "Unknown Artist" in rec.artists
        )

        if tracks_needing_enrichment == 0:
            logger.info("No tracks need enrichment - all have valid Spotify URIs")
            return {"can_proceed": False, "access_token": access_token, "tracks_needing_enrichment": 0}

        logger.info(
            f"Found {tracks_needing_enrichment}/{len(state.recommendations)} tracks "
            f"that need enrichment"
        )
        
        return {
            "can_proceed": True,
            "access_token": access_token,
            "tracks_needing_enrichment": tracks_needing_enrichment
        }

    async def process_track_enrichment(
        self,
        state: AgentState,
        access_token: str,
        tracks_needing_enrichment: int
    ) -> AgentState:
        """Process the actual track enrichment."""
        # Enrich recommendations
        state.current_step = "enriching_tracks"
        await self._notify_progress(state)

        enriched_recommendations = await self.track_enrichment_service.enrich_recommendations(
            recommendations=state.recommendations,
            access_token=access_token
        )

        # Update state with enriched recommendations
        original_count = len(state.recommendations)
        state.recommendations = enriched_recommendations

        logger.info(
            f"Track enrichment complete: "
            f"{original_count} -> {len(enriched_recommendations)} tracks "
            f"({original_count - len(enriched_recommendations)} removed)"
        )

        # Store enrichment metadata
        state.metadata["track_enrichment"] = {
            "original_count": original_count,
            "enriched_count": len(enriched_recommendations),
            "removed_count": original_count - len(enriched_recommendations),
            "tracks_needing_enrichment": tracks_needing_enrichment
        }
        
        return state