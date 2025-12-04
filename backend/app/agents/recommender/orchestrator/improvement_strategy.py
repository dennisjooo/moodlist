"""Improvement strategy for deciding and applying playlist improvements."""

import structlog
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...states.agent_state import AgentState
from ...core.base_agent import BaseAgent
from ..utils.llm_response_parser import LLMResponseParser
from .prompts import get_strategy_decision_prompt

logger = structlog.get_logger(__name__)


class ImprovementStrategy:
    """Handles improvement strategy decision and application for playlists."""

    def __init__(
        self,
        recommendation_generator: BaseAgent,
        llm: Optional[BaseLanguageModel] = None,
        cohesion_threshold: float = 0.65,
    ):
        """Initialize the improvement strategy handler.

        Args:
            recommendation_generator: Agent for generating more recommendations
            llm: Language model for strategy decision
            cohesion_threshold: Minimum cohesion score threshold
        """
        self.recommendation_generator = recommendation_generator
        self.llm = llm
        self.cohesion_threshold = cohesion_threshold

    async def decide_improvement_strategy(
        self, quality_evaluation: Dict[str, Any], state: AgentState
    ) -> List[str]:
        """Decide which improvement strategies to apply based on quality evaluation.

        Uses LLM to intelligently select compound strategies.

        Args:
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            List of strategy names to apply (can be multiple for compound strategy)
        """
        # Use LLM to decide strategy if available
        if self.llm:
            llm_strategies = await self._llm_decide_strategy(state, quality_evaluation)
            if llm_strategies:
                logger.info(f"LLM suggested strategies: {llm_strategies}")
                return llm_strategies

        # Fallback to rule-based compound strategy selection
        strategies = []
        outlier_count = len(quality_evaluation.get("outlier_tracks", []))
        cohesion_score = quality_evaluation.get("cohesion_score", 0)
        recommendations_count = quality_evaluation.get("recommendations_count", 0)

        # Get target from plan
        playlist_target = state.metadata.get("playlist_target", {})
        min_count = playlist_target.get("min_count", 15)
        target_count = playlist_target.get("target_count", 20)

        # Strategy 1: Filter outliers if present
        if outlier_count > 0 and recommendations_count > min_count:
            strategies.append("filter_and_replace")

        # Strategy 2: Adjust feature weights if cohesion needs improvement
        if cohesion_score < self.cohesion_threshold:
            strategies.append("adjust_feature_weights")

        # Strategy 3: Re-seed if cohesion is very poor
        if cohesion_score < 0.6 and recommendations_count >= min_count:
            if "filter_and_replace" not in strategies:
                strategies.append("reseed_from_clean")

        # Strategy 4: Generate more if count is insufficient
        if recommendations_count < target_count:
            strategies.append("generate_more")

        # Default: at least adjust and generate
        if not strategies:
            strategies = ["adjust_feature_weights", "generate_more"]

        return strategies

    async def apply_improvements(
        self,
        strategies: List[str],
        quality_evaluation: Dict[str, Any],
        state: AgentState,
    ) -> AgentState:
        """Apply multiple improvement strategies in sequence (compound strategy).

        Args:
            strategies: List of improvement strategies to apply
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            Updated agent state
        """
        state.metadata["improvement_actions"].append(
            {
                "strategies": strategies,
                "iteration": state.metadata["orchestration_iterations"],
            }
        )

        # Apply each strategy in order
        for strategy in strategies:
            logger.info(f"Applying strategy: {strategy}")

            if strategy == "filter_and_replace":
                state = await self._filter_and_replace(quality_evaluation, state)
            elif strategy == "reseed_from_clean":
                state = await self._reseed_from_clean(quality_evaluation, state)
            elif strategy == "adjust_feature_weights":
                state = await self._adjust_feature_weights(state)
            elif strategy == "generate_more":
                state = await self._generate_more_recommendations(state)
            else:
                logger.warning(f"Unknown improvement strategy: {strategy}")

        return state

    async def _filter_and_replace(
        self, quality_evaluation: Dict[str, Any], state: AgentState
    ) -> AgentState:
        """Remove outlier tracks and generate replacements using good tracks as seeds.

        Args:
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            Updated agent state
        """
        outlier_ids = set(quality_evaluation.get("outlier_tracks", []))

        # Filter out outliers BUT ALWAYS KEEP protected tracks (user-mentioned)
        good_recommendations = []
        protected_kept = 0
        for rec in state.recommendations:
            if rec.track_id in outlier_ids:
                # Check if this is a protected track
                if rec.protected or rec.user_mentioned:
                    # CRITICAL: Never filter user-mentioned tracks
                    logger.info(
                        f"Keeping outlier because it's protected: {rec.track_name} by {', '.join(rec.artists)} "
                        f"(user_mentioned={rec.user_mentioned})"
                    )
                    good_recommendations.append(rec)
                    protected_kept += 1
                    outlier_ids.discard(rec.track_id)  # Remove from outlier set
                # else: filter it out (don't add to good_recommendations)
            else:
                good_recommendations.append(rec)

        logger.info(
            f"Filtering {len(outlier_ids)} outliers, keeping {len(good_recommendations)} good tracks "
            f"({protected_kept} protected tracks kept despite being outliers)"
        )

        # Add outliers to negative seeds (limit to 5 for RecoBeat API)
        if outlier_ids:
            # Add new outliers to existing negative seeds
            existing_negative_seeds = set(state.negative_seeds)
            existing_negative_seeds.update(outlier_ids)

            # Keep only most recent 5 negative seeds
            state.negative_seeds = list(existing_negative_seeds)[-5:]

            logger.info(
                f"Added {len(outlier_ids)} outliers as negative seeds (total: {len(state.negative_seeds)})"
            )

            # Track in metadata
            if "orchestration_negative_seeds_used" not in state.metadata:
                state.metadata["orchestration_negative_seeds_used"] = []
            state.metadata["orchestration_negative_seeds_used"].append(
                {
                    "iteration": state.metadata.get("orchestration_iterations", 0),
                    "outliers_added": list(outlier_ids),
                    "total_negative_seeds": len(state.negative_seeds),
                }
            )

        # Use good tracks as new seeds
        new_seeds = [rec.track_id for rec in good_recommendations[:5]]

        if new_seeds:
            state.seed_tracks = new_seeds
            state.recommendations = good_recommendations

            # Generate replacement recommendations
            state = await self.recommendation_generator.run_with_error_handling(state)

        return state

    async def _reseed_from_clean(
        self, quality_evaluation: Dict[str, Any], state: AgentState
    ) -> AgentState:
        """Use top-scoring tracks from current recommendations as seeds for next iteration.

        Args:
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            Updated agent state
        """
        # Sort recommendations by confidence and cohesion
        track_scores = quality_evaluation.get("track_scores", {})

        scored_recs = [
            (rec, (rec.confidence_score + track_scores.get(rec.track_id, 0.5)) / 2)
            for rec in state.recommendations
        ]
        scored_recs.sort(key=lambda x: x[1], reverse=True)

        # Take top tracks as new seeds
        top_tracks = scored_recs[:5]
        new_seeds = [rec.track_id for rec, _ in top_tracks]

        # Add bottom tracks as negative seeds (but NEVER protected tracks)
        bottom_tracks = scored_recs[-3:]  # Take bottom 3
        outlier_ids = []
        for rec, score in bottom_tracks:
            # CRITICAL: Never add protected tracks to negative seeds
            if not (rec.protected or rec.user_mentioned):
                outlier_ids.append(rec.track_id)
            else:
                logger.info(
                    f"Skipping protected track from negative seeds: {rec.track_name} "
                    f"(user_mentioned={rec.user_mentioned})"
                )

        if outlier_ids:
            # Add to negative seeds
            existing_negative_seeds = set(state.negative_seeds)
            existing_negative_seeds.update(outlier_ids)

            # Keep only most recent 5
            state.negative_seeds = list(existing_negative_seeds)[-5:]

            logger.info(
                f"Added {len(outlier_ids)} low-scoring tracks as negative seeds"
            )

        logger.info(f"Re-seeding with {len(new_seeds)} top-scoring tracks")

        # Keep top tracks and generate more around them
        state.recommendations = [rec for rec, _ in top_tracks]
        state.seed_tracks = new_seeds

        # Generate new recommendations
        state = await self.recommendation_generator.run_with_error_handling(state)

        return state

    async def _adjust_feature_weights(self, state: AgentState) -> AgentState:
        """Adjust feature weights to be stricter for next recommendation generation.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with adjusted feature weights
        """
        # Increase feature_weight for stricter mood matching
        current_weight = state.metadata.get("feature_weight", 4.5)
        new_weight = min(current_weight + 0.3, 5.0)

        state.metadata["feature_weight"] = new_weight

        logger.info(f"Adjusted feature weight from {current_weight} to {new_weight}")

        return state

    async def _generate_more_recommendations(self, state: AgentState) -> AgentState:
        """Generate additional recommendations to reach target count.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with more recommendations
        """
        current_count = len(state.recommendations)

        # Get target from plan
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)

        # Calculate how many more we need
        needed = max(target_count - current_count, 5)

        logger.info(
            f"Generating {needed} more recommendations "
            f"(current: {current_count}, target: {target_count})"
        )

        previous_count = len(state.recommendations)

        # Generate new recommendations
        state = await self.recommendation_generator.run_with_error_handling(state)

        logger.info(
            "Generated additional recommendations",
            previous_count=previous_count,
            new_count=len(state.recommendations),
        )

        return state

    async def _llm_decide_strategy(
        self, state: AgentState, quality_evaluation: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Use LLM to intelligently decide improvement strategies.

        Args:
            state: Current agent state
            quality_evaluation: Quality evaluation results

        Returns:
            List of strategies to apply (compound strategy)
        """
        try:
            issues_summary = "\n".join(
                f"- {issue}" for issue in quality_evaluation.get("issues", [])
            )
            llm_assessment = quality_evaluation.get("llm_assessment", {})
            playlist_target = state.metadata.get("playlist_target", {})
            target_count = playlist_target.get("target_count", 20)

            prompt = get_strategy_decision_prompt(
                mood_prompt=state.mood_prompt,
                quality_evaluation=quality_evaluation,
                issues_summary=issues_summary,
                llm_assessment_reasoning=(llm_assessment or {}).get("reasoning", "N/A"),
                target_count=target_count,
                iteration=state.metadata.get("orchestration_iterations", 0),
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            # Parse JSON response using centralized parser
            strategy_decision = LLMResponseParser.extract_json_from_response(response)

            if strategy_decision:
                strategies = strategy_decision.get("strategies", [])
                reasoning = strategy_decision.get("reasoning", "")

                logger.info(f"LLM strategy decision: {strategies}")
                logger.info(f"LLM reasoning: {reasoning}")

                # Validate strategies
                valid_strategies = [
                    "filter_and_replace",
                    "reseed_from_clean",
                    "adjust_feature_weights",
                    "generate_more",
                ]
                filtered_strategies = [s for s in strategies if s in valid_strategies]

                return filtered_strategies if filtered_strategies else None
            else:
                logger.warning("Could not parse LLM strategy decision response")
                return None

        except Exception as e:
            logger.error(f"LLM strategy decision failed: {str(e)}", exc_info=True)
            return None
