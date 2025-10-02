"""Orchestrator agent for evaluating and improving playlist quality."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus, TrackRecommendation


logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Agent for orchestrating quality evaluation and iterative improvement of playlists."""

    def __init__(
        self,
        mood_analyzer: BaseAgent,
        recommendation_generator: BaseAgent,
        seed_gatherer: BaseAgent,
        llm: Optional[BaseLanguageModel] = None,
        max_iterations: int = 3,
        cohesion_threshold: float = 0.75,
        verbose: bool = False
    ):
        """Initialize the orchestrator agent.

        Args:
            mood_analyzer: MoodAnalyzerAgent instance for re-analysis if needed
            recommendation_generator: RecommendationGeneratorAgent for generating more tracks
            seed_gatherer: SeedGathererAgent for re-seeding if needed
            llm: Language model for decision making
            max_iterations: Maximum improvement iterations before accepting results
            cohesion_threshold: Minimum cohesion score (0-1) to accept playlist
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
            if "orchestration_iterations" not in state.metadata:
                state.metadata["orchestration_iterations"] = 0
            if "quality_scores" not in state.metadata:
                state.metadata["quality_scores"] = []
            if "improvement_actions" not in state.metadata:
                state.metadata["improvement_actions"] = []

            # Initial seed gathering and recommendation generation
            logger.info("Initial seed gathering...")
            state.current_step = "gathering_seeds"
            state.status = RecommendationStatus.GATHERING_SEEDS
            state = await self.seed_gatherer.run_with_error_handling(state)

            logger.info("Initial recommendation generation...")
            state.current_step = "generating_recommendations"
            state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS
            state = await self.recommendation_generator.run_with_error_handling(state)

            # Iterative improvement loop
            for iteration in range(self.max_iterations):
                state.metadata["orchestration_iterations"] = iteration + 1
                state.current_step = f"evaluating_quality_iteration_{iteration + 1}"
                state.status = RecommendationStatus.EVALUATING_QUALITY

                # Evaluate current playlist quality
                quality_evaluation = await self.evaluate_playlist_quality(state)
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


                # Apply improvement strategies (can be compound)
                state.current_step = f"optimizing_recommendations_iteration_{iteration + 1}"
                state.status = RecommendationStatus.OPTIMIZING_RECOMMENDATIONS

                improvement_strategies = await self.decide_improvement_strategy(
                    quality_evaluation, state
                )
                logger.info(f"Applying improvement strategies: {improvement_strategies}")

                state = await self.apply_improvements(
                    improvement_strategies, quality_evaluation, state
                )

                # Small delay between iterations
                await asyncio.sleep(0.1)

            # Final state update
            state.current_step = "recommendations_ready"
            state.metadata["final_quality_evaluation"] = quality_evaluation

            # Remove duplicates
            state.recommendations = self._remove_duplicates(state.recommendations)

            # Cap recommendations at max_count to respect target plan
            playlist_target = state.metadata.get("playlist_target", {})
            max_count = playlist_target.get("max_count", 30)
            
            if len(state.recommendations) > max_count:
                # Keep the highest confidence recommendations
                state.recommendations.sort(key=lambda r: r.confidence_score, reverse=True)
                original_count = len(state.recommendations)
                state.recommendations = state.recommendations[:max_count]
                logger.info(
                    f"Capped recommendations at max_count: {original_count} -> {max_count} tracks"
                )

            logger.info(
                f"Orchestration completed with {len(state.recommendations)} unique recommendations "
                f"after {state.metadata['orchestration_iterations']} iteration(s)"
            )

        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}", exc_info=True)
            state.set_error(f"Orchestration failed: {str(e)}")

        return state

    def _remove_duplicates(self, recommendations: List[TrackRecommendation]) -> List[TrackRecommendation]:
        """Remove duplicate tracks from recommendations.

        Args:
            recommendations: List of track recommendations

        Returns:
            List with duplicates removed, preserving order and keeping first occurrence
        """
        seen_track_ids = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec.track_id not in seen_track_ids:
                seen_track_ids.add(rec.track_id)
                unique_recommendations.append(rec)
            else:
                logger.debug(f"Removing duplicate: {rec.track_name} by {', '.join(rec.artists)}")
        
        if len(unique_recommendations) < len(recommendations):
            logger.info(f"Removed {len(recommendations) - len(unique_recommendations)} duplicate tracks")
        
        return unique_recommendations
    
    async def evaluate_playlist_quality(self, state: AgentState) -> Dict[str, Any]:
        """Evaluate the quality of current recommendations against mood criteria.

        Args:
            state: Current agent state with recommendations

        Returns:
            Quality evaluation dictionary with scores and issues
        """
        recommendations = state.recommendations
        target_features = state.metadata.get("target_features", {})
        feature_weights = state.metadata.get("feature_weights", {})
        
        # Get target plan
        playlist_target = state.metadata.get("playlist_target", {})
        min_count = playlist_target.get("min_count", 15)
        target_count = playlist_target.get("target_count", 20)
        quality_threshold = playlist_target.get("quality_threshold", 0.75)

        evaluation = {
            "overall_score": 0.0,
            "cohesion_score": 0.0,
            "coverage_score": 0.0,
            "confidence_score": 0.0,
            "diversity_score": 0.0,
            "meets_threshold": False,
            "issues": [],
            "recommendations_count": len(recommendations),
            "target_count": target_count,  # Track target
            "outlier_tracks": [],
            "llm_assessment": None
        }

        # Check against minimum (not target, minimum is the floor)
        if len(recommendations) < min_count:
            evaluation["issues"].append(
                f"Below minimum: {len(recommendations)} < {min_count}"
            )
            evaluation["coverage_score"] = len(recommendations) / target_count
        # Check if we're close to target
        elif len(recommendations) < target_count:
            evaluation["coverage_score"] = len(recommendations) / target_count
            evaluation["issues"].append(
                f"Below target: {len(recommendations)} < {target_count}"
            )
        else:
            evaluation["coverage_score"] = 1.0

        if len(recommendations) == 0:
            return evaluation

        # Calculate cohesion score
        cohesion_result = self.calculate_cohesion_score(
            recommendations, target_features, feature_weights
        )
        evaluation["cohesion_score"] = cohesion_result["score"]
        evaluation["outlier_tracks"] = cohesion_result["outliers"]

        if cohesion_result["outliers"]:
            evaluation["issues"].append(
                f"Found {len(cohesion_result['outliers'])} outlier tracks"
            )

        # Calculate average confidence score
        avg_confidence = sum(r.confidence_score for r in recommendations) / len(recommendations)
        evaluation["confidence_score"] = avg_confidence

        if avg_confidence < 0.5:
            evaluation["issues"].append(f"Low average confidence: {avg_confidence:.2f}")

        # Calculate diversity score (artist variety)
        unique_artists = set()
        for rec in recommendations:
            unique_artists.update(rec.artists)
        
        # Good diversity: at least 60% unique artists relative to track count
        artist_diversity_ratio = len(unique_artists) / max(len(recommendations), 1)
        evaluation["diversity_score"] = min(artist_diversity_ratio / 0.6, 1.0)

        # Calculate overall score (weighted average)
        evaluation["overall_score"] = (
            evaluation["cohesion_score"] * 0.4 +
            evaluation["coverage_score"] * 0.25 +
            evaluation["confidence_score"] * 0.2 +
            evaluation["diversity_score"] * 0.15
        )

        # Use LLM to assess playlist quality if available
        if self.llm:
            llm_assessment = await self._llm_evaluate_quality(state, evaluation)
            evaluation["llm_assessment"] = llm_assessment
            
            # Adjust overall score based on LLM assessment
            if llm_assessment:
                llm_score = llm_assessment.get("quality_score", 0.5)
                # Blend algorithmic and LLM scores (70% algo, 30% LLM)
                evaluation["overall_score"] = (
                    evaluation["overall_score"] * 0.7 + llm_score * 0.3
                )
                
                # Update issues with LLM insights
                if llm_assessment.get("issues"):
                    evaluation["issues"].extend(llm_assessment["issues"])

        # Check if meets threshold using target's quality threshold
        evaluation["meets_threshold"] = (
            evaluation["cohesion_score"] >= self.cohesion_threshold and
            len(recommendations) >= target_count and  # Must reach target, not just min
            len(evaluation["outlier_tracks"]) == 0 and
            evaluation["overall_score"] >= quality_threshold  # Use target's threshold
        )

        return evaluation

    def calculate_cohesion_score(
        self,
        recommendations: List[TrackRecommendation],
        target_features: Dict[str, Any],
        feature_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Calculate how cohesive the recommendations are relative to target mood.

        Args:
            recommendations: List of track recommendations
            target_features: Target audio features from mood analysis
            feature_weights: Importance weights for each feature (0-1)

        Returns:
            Dictionary with cohesion score and list of outlier track IDs
        """
        if not target_features or not recommendations:
            return {"score": 0.5, "outliers": [], "track_scores": {}}

        # Use provided feature weights or defaults
        if not feature_weights:
            feature_weights = {
                "energy": 0.8,
                "valence": 0.8,
                "speechiness": 0.7,
                "instrumentalness": 0.7,
                "danceability": 0.6,
                "acousticness": 0.6,
                "tempo": 0.4,
                "mode": 0.4,
                "loudness": 0.3,
                "liveness": 0.2,
                "key": 0.2,
                "popularity": 0.1
            }

        # Stricter tolerance thresholds for cohesion checking
        tolerance_thresholds = {
            "speechiness": 0.20,
            "instrumentalness": 0.20,
            "energy": 0.25,
            "valence": 0.25,
            "danceability": 0.25,
            "tempo": 35.0,
            "loudness": 5.0,
            "acousticness": 0.30,
            "liveness": 0.30,
            "popularity": 25
        }

        # Critical features are those with high weights (>0.65)
        critical_features = [
            feature for feature, weight in feature_weights.items()
            if weight > 0.65
        ]

        track_scores = {}
        outliers = []
        cohesion_scores = []

        for rec in recommendations:
            if not rec.audio_features:
                # Tracks without features get neutral score
                track_scores[rec.track_id] = 0.7
                cohesion_scores.append(0.7)
                continue

            violations = []
            weighted_violations = 0.0  # Sum of weights for violated features
            weighted_matches = []

            for feature_name, target_value in target_features.items():
                if feature_name not in rec.audio_features:
                    continue

                actual_value = rec.audio_features[feature_name]
                tolerance = tolerance_thresholds.get(feature_name)

                if tolerance is None:
                    continue

                # Get weight for this feature (default to 0.5 if not specified)
                weight = feature_weights.get(feature_name, 0.5)

                # Convert target value to single number if it's a range
                if isinstance(target_value, list) and len(target_value) == 2:
                    target_single = sum(target_value) / 2
                elif isinstance(target_value, (int, float)):
                    target_single = float(target_value)
                else:
                    continue

                # Calculate difference
                difference = abs(actual_value - target_single)
                
                # Calculate match score for this feature (1.0 = perfect, 0.0 = max difference)
                match_score = max(0.0, 1.0 - (difference / tolerance))
                
                # Weight the match score
                weighted_matches.append((match_score, weight))

                # Check for violations with weighted importance
                if difference > tolerance:
                    violations.append(feature_name)
                    weighted_violations += weight

            # Calculate weighted average track cohesion score
            if weighted_matches:
                total_weight = sum(w for _, w in weighted_matches)
                weighted_sum = sum(score * w for score, w in weighted_matches)
                track_cohesion = weighted_sum / total_weight if total_weight > 0 else 0.0
            else:
                track_cohesion = 0.7  # Neutral score if no features to compare

            track_scores[rec.track_id] = track_cohesion

            # Mark as outlier based on weighted violations and cohesion score
            # Outlier if: high weighted violations (>1.5) OR critical feature + low cohesion
            is_critical_violation = any(f in critical_features for f in violations)
            
            if weighted_violations > 1.5 or (is_critical_violation and track_cohesion < 0.5):
                outliers.append(rec.track_id)
                logger.debug(
                    f"Outlier detected: {rec.track_name} by {', '.join(rec.artists)} "
                    f"(score={track_cohesion:.2f}, weighted_violations={weighted_violations:.2f}, "
                    f"violations={violations})"
                )
            else:
                cohesion_scores.append(track_cohesion)

        # Calculate overall cohesion score (excluding outliers)
        if cohesion_scores:
            overall_cohesion = sum(cohesion_scores) / len(cohesion_scores)
        else:
            overall_cohesion = 0.0

        return {
            "score": overall_cohesion,
            "outliers": outliers,
            "track_scores": track_scores
        }

    async def decide_improvement_strategy(
        self,
        quality_evaluation: Dict[str, Any],
        state: AgentState
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
        issues = quality_evaluation.get("issues", [])
        outlier_count = len(quality_evaluation.get("outlier_tracks", []))
        cohesion_score = quality_evaluation.get("cohesion_score", 0)
        recommendations_count = quality_evaluation.get("recommendations_count", 0)

        # Strategy 1: Filter outliers if present
        if outlier_count > 0 and recommendations_count > self.min_recommendations:
            strategies.append("filter_and_replace")

        # Strategy 2: Adjust feature weights if cohesion needs improvement
        if cohesion_score < self.cohesion_threshold:
            strategies.append("adjust_feature_weights")

        # Strategy 3: Re-seed if cohesion is very poor
        if cohesion_score < 0.6 and recommendations_count >= self.min_recommendations:
            if "filter_and_replace" not in strategies:
                strategies.append("reseed_from_clean")

        # Strategy 4: Generate more if count is insufficient
        if recommendations_count < self.min_recommendations:
            strategies.append("generate_more")

        # Default: at least adjust and generate
        if not strategies:
            strategies = ["adjust_feature_weights", "generate_more"]

        return strategies

    async def apply_improvements(
        self,
        strategies: List[str],
        quality_evaluation: Dict[str, Any],
        state: AgentState
    ) -> AgentState:
        """Apply multiple improvement strategies in sequence (compound strategy).

        Args:
            strategies: List of improvement strategies to apply
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            Updated agent state
        """
        state.metadata["improvement_actions"].append({
            "strategies": strategies,
            "iteration": state.metadata["orchestration_iterations"]
        })

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
        self,
        quality_evaluation: Dict[str, Any],
        state: AgentState
    ) -> AgentState:
        """Remove outlier tracks and generate replacements using good tracks as seeds.

        Args:
            quality_evaluation: Quality evaluation results
            state: Current agent state

        Returns:
            Updated agent state
        """
        outlier_ids = set(quality_evaluation.get("outlier_tracks", []))
        
        # Filter out outliers
        good_recommendations = [
            rec for rec in state.recommendations
            if rec.track_id not in outlier_ids
        ]

        logger.info(
            f"Filtering {len(outlier_ids)} outliers, keeping {len(good_recommendations)} good tracks"
        )

        # Add outliers to negative seeds (limit to 5 for RecoBeat API)
        if outlier_ids:
            # Add new outliers to existing negative seeds
            existing_negative_seeds = set(state.negative_seeds)
            existing_negative_seeds.update(outlier_ids)
            
            # Keep only most recent 5 negative seeds
            state.negative_seeds = list(existing_negative_seeds)[-5:]
            
            logger.info(f"Added {len(outlier_ids)} outliers as negative seeds (total: {len(state.negative_seeds)})")
            
            # Track in metadata
            if "orchestration_negative_seeds_used" not in state.metadata:
                state.metadata["orchestration_negative_seeds_used"] = []
            state.metadata["orchestration_negative_seeds_used"].append({
                "iteration": state.metadata.get("orchestration_iterations", 0),
                "outliers_added": list(outlier_ids),
                "total_negative_seeds": len(state.negative_seeds)
            })

        # Use good tracks as new seeds
        new_seeds = [rec.track_id for rec in good_recommendations[:5]]
        
        if new_seeds:
            state.seed_tracks = new_seeds
            state.recommendations = good_recommendations

            # Generate replacement recommendations
            state = await self.recommendation_generator.run_with_error_handling(state)

        return state

    async def _reseed_from_clean(
        self,
        quality_evaluation: Dict[str, Any],
        state: AgentState
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
        
        # Add bottom tracks as negative seeds
        bottom_tracks = scored_recs[-3:]  # Take bottom 3
        outlier_ids = [rec.track_id for rec, _ in bottom_tracks]
        
        if outlier_ids:
            # Add to negative seeds
            existing_negative_seeds = set(state.negative_seeds)
            existing_negative_seeds.update(outlier_ids)
            
            # Keep only most recent 5
            state.negative_seeds = list(existing_negative_seeds)[-5:]
            
            logger.info(f"Added {len(outlier_ids)} low-scoring tracks as negative seeds")

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

        # Store current recommendations temporarily
        existing_recommendations = state.recommendations.copy()

        # Generate new recommendations
        state = await self.recommendation_generator.run_with_error_handling(state)

        # The recommendation generator will add to existing recommendations

        return state

    async def _llm_evaluate_quality(
        self,
        state: AgentState,
        evaluation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to evaluate playlist quality with contextual understanding.

        Args:
            state: Current agent state
            evaluation: Algorithmic evaluation results

        Returns:
            LLM assessment with quality score and insights
        """
        try:
            # Prepare playlist summary for LLM (first 10 tracks for brevity)
            tracks_summary = []
            for i, rec in enumerate(state.recommendations[:10], 1):
                tracks_summary.append(
                    f"{i}. {rec.track_name} by {', '.join(rec.artists)} "
                    f"(confidence: {rec.confidence_score:.2f})"
                )
            
            mood_interpretation = state.mood_analysis.get("mood_interpretation", "N/A")
            target_features = state.metadata.get("target_features", {})
            playlist_target = state.metadata.get("playlist_target", {})
            target_count = playlist_target.get("target_count", 20)
            
            prompt = f"""You are a music curator expert evaluating a playlist for quality and cohesion.

**User's Mood Request**: "{state.mood_prompt}"

**Mood Analysis**: {mood_interpretation}

**Target Audio Features**: {', '.join(f'{k}={v:.2f}' for k, v in list(target_features.items())[:5])}

**Playlist** ({len(state.recommendations)} tracks, target: {target_count}):
{chr(10).join(tracks_summary)}

**Algorithmic Metrics**:
- Cohesion Score: {evaluation['cohesion_score']:.2f}/1.0
- Confidence Score: {evaluation['confidence_score']:.2f}/1.0
- Diversity Score: {evaluation['diversity_score']:.2f}/1.0
- Outliers Found: {len(evaluation['outlier_tracks'])}
- Overall Score: {evaluation['overall_score']:.2f}/1.0

**Task**: Evaluate if this playlist truly matches the user's mood and maintains good cohesion. Consider:
1. Do the tracks fit the requested mood and vibe?
2. Is there good variety without jarring genre shifts?
3. Would these tracks flow well together?
4. Are there any tracks that feel out of place?

Respond in JSON format:
{{
  "quality_score": <float 0-1>,
  "meets_expectations": <boolean>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "issues": ["<issue 1>", "<issue 2>"],
  "specific_concerns": ["<track name> feels out of place because..."],
  "reasoning": "<brief explanation>"
}}"""

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                assessment = json.loads(json_str)
                logger.info(f"LLM assessment: quality={assessment.get('quality_score')}, "
                           f"meets_expectations={assessment.get('meets_expectations')}")
                return assessment
            else:
                logger.warning("Could not parse LLM quality assessment response")
                return None
                
        except Exception as e:
            logger.error(f"LLM quality evaluation failed: {str(e)}", exc_info=True)
            return None

    async def _llm_decide_strategy(
        self,
        state: AgentState,
        quality_evaluation: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Use LLM to intelligently decide improvement strategies.

        Args:
            state: Current agent state
            quality_evaluation: Quality evaluation results

        Returns:
            List of strategies to apply (compound strategy)
        """
        try:
            issues_summary = "\n".join(f"- {issue}" for issue in quality_evaluation.get("issues", []))
            llm_assessment = quality_evaluation.get("llm_assessment", {})
            playlist_target = state.metadata.get("playlist_target", {})
            target_count = playlist_target.get("target_count", 20)
            
            prompt = f"""You are a music recommendation system optimizer deciding how to improve a playlist.

**Current Situation**:
- Mood: "{state.mood_prompt}"
- Current: {quality_evaluation['recommendations_count']} tracks
- Target: {target_count} tracks
- Cohesion Score: {quality_evaluation['cohesion_score']:.2f}/1.0
- Overall Score: {quality_evaluation['overall_score']:.2f}/1.0
- Outliers: {len(quality_evaluation['outlier_tracks'])} tracks
- Iteration: {state.metadata.get('orchestration_iterations', 0)}/3

**Issues**:
{issues_summary or "No major issues detected"}

**LLM Assessment**: {llm_assessment.get('reasoning', 'N/A')}

**Available Strategies** (can select multiple for compound approach):
1. "filter_and_replace" - Remove outlier tracks and generate replacements
2. "reseed_from_clean" - Use best current tracks as seeds for new generation
3. "adjust_feature_weights" - Make mood matching stricter
4. "generate_more" - Add more recommendations to reach target count

**Task**: Select 1-3 strategies that would best improve this playlist. Consider:
- Multiple strategies can work together (compound approach)
- Order matters (strategies execute sequentially)
- Balance between quality and maintaining sufficient recommendations

Respond in JSON format:
{{
  "strategies": ["<strategy1>", "<strategy2>"],
  "reasoning": "<why these strategies in this order>"
}}"""

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                strategy_decision = json.loads(json_str)
                strategies = strategy_decision.get("strategies", [])
                reasoning = strategy_decision.get("reasoning", "")
                
                logger.info(f"LLM strategy decision: {strategies}")
                logger.info(f"LLM reasoning: {reasoning}")
                
                # Validate strategies
                valid_strategies = [
                    "filter_and_replace", "reseed_from_clean",
                    "adjust_feature_weights", "generate_more"
                ]
                filtered_strategies = [s for s in strategies if s in valid_strategies]
                
                return filtered_strategies if filtered_strategies else None
            else:
                logger.warning("Could not parse LLM strategy decision response")
                return None
                
        except Exception as e:
            logger.error(f"LLM strategy decision failed: {str(e)}", exc_info=True)
            return None

