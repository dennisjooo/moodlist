"""Quality evaluator for assessing playlist quality against mood criteria."""

import structlog
from typing import Any, Dict, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...states.agent_state import AgentState
from ..utils.llm_response_parser import LLMResponseParser
from .cohesion_calculator import CohesionCalculator
from .prompts import get_quality_evaluation_prompt

logger = structlog.get_logger(__name__)


class QualityEvaluator:
    """Evaluates the quality of playlists against mood criteria."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        cohesion_threshold: float = 0.65
    ):
        """Initialize the quality evaluator.

        Args:
            llm: Language model for quality assessment
            cohesion_threshold: Minimum cohesion score threshold
        """
        self.llm = llm
        self.cohesion_threshold = cohesion_threshold
        self.cohesion_calculator = CohesionCalculator()

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
        cohesion_result = self.cohesion_calculator.calculate_cohesion_score(
            recommendations, target_features, feature_weights
        )
        evaluation["cohesion_score"] = cohesion_result["score"]
        evaluation["outlier_tracks"] = cohesion_result["outliers"]
        evaluation["track_scores"] = cohesion_result["track_scores"]

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
                
                # CRITICAL: Extract LLM-identified outliers from specific_concerns
                llm_outliers = self.cohesion_calculator.extract_llm_outliers(
                    llm_assessment.get("specific_concerns", []),
                    recommendations
                )
                if llm_outliers:
                    # Merge with algorithmic outliers (union, not duplicates)
                    existing_outliers = set(evaluation["outlier_tracks"])
                    existing_outliers.update(llm_outliers)
                    evaluation["outlier_tracks"] = list(existing_outliers)
                    
                    logger.info(
                        f"LLM identified {len(llm_outliers)} additional outliers: "
                        f"{[r.track_name for r in recommendations if r.track_id in llm_outliers]}"
                    )

        # Check if meets threshold using target's quality threshold
        # Relaxed: cohesion >= 0.65 AND overall >= 0.60 OR (cohesion >= 0.70 with some outliers)
        meets_strict = (
            evaluation["cohesion_score"] >= self.cohesion_threshold and
            len(recommendations) >= target_count and
            len(evaluation["outlier_tracks"]) == 0 and
            evaluation["overall_score"] >= quality_threshold
        )
        meets_relaxed = (
            evaluation["cohesion_score"] >= 0.65 and
            evaluation["overall_score"] >= 0.60 and
            len(recommendations) >= min_count and
            len(evaluation["outlier_tracks"]) <= 2  # Allow up to 2 minor outliers
        )
        evaluation["meets_threshold"] = meets_strict or meets_relaxed

        return evaluation

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
            # Prepare playlist summary for LLM (first 15 tracks for better assessment)
            tracks_summary = []
            for i, rec in enumerate(state.recommendations[:15], 1):
                tracks_summary.append(
                    f"{i}. {rec.track_name} by {', '.join(rec.artists)} "
                    f"(confidence: {rec.confidence_score:.2f}, source: {rec.source})"
                )
            
            mood_interpretation = state.mood_analysis.get("mood_interpretation", "N/A")
            artist_recommendations = state.mood_analysis.get("artist_recommendations", [])
            genre_keywords = state.mood_analysis.get("genre_keywords", [])
            target_features = state.metadata.get("target_features", {})
            playlist_target = state.metadata.get("playlist_target", {})
            target_count = playlist_target.get("target_count", 20)
            
            prompt = get_quality_evaluation_prompt(
                mood_prompt=state.mood_prompt,
                mood_interpretation=mood_interpretation,
                artist_recommendations=artist_recommendations,
                genre_keywords=genre_keywords,
                target_features=target_features,
                tracks_summary=chr(10).join(tracks_summary),
                target_count=target_count,
                evaluation=evaluation
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            
            # Parse JSON response using centralized parser
            assessment = LLMResponseParser.extract_json_from_response(response)
            
            if assessment:
                logger.info(f"LLM assessment: quality={assessment.get('quality_score')}, "
                           f"meets_expectations={assessment.get('meets_expectations')}")
                return assessment
            else:
                logger.warning("Could not parse LLM quality assessment response")
                return None
                
        except Exception as e:
            logger.error(f"LLM quality evaluation failed: {str(e)}", exc_info=True)
            return None