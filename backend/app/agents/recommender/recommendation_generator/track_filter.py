"""Track filtering and validation utilities."""

import logging
from typing import Any, Dict, List, Optional

from ...states.agent_state import TrackRecommendation
from ..utils import TrackRecommendationFactory, RecommendationValidator, ValidationResult

logger = logging.getLogger(__name__)


class TrackFilter:
    """Handles track validation and filtering based on mood analysis."""

    def validate_track_relevance(
        self,
        track_name: str,
        artists: List[str],
        mood_analysis: Optional[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """Validate if a track is relevant to the mood before accepting.

        Filters out obvious mismatches (wrong language, genre, etc.)

        Args:
            track_name: Track name to validate
            artists: List of artist names
            mood_analysis: Mood analysis with artist recommendations and keywords

        Returns:
            (is_valid, reason) - True if track is relevant, False with reason if not
        """
        result = RecommendationValidator.validate_track_relevance(track_name, artists, mood_analysis)
        return result.is_valid, result.reason

    def _apply_mood_filtering(
        self,
        recommendations: List[TrackRecommendation],
        mood_analysis: Dict[str, Any]
    ) -> List[TrackRecommendation]:
        """Apply mood-based filtering to recommendations using range-based logic.

        Args:
            recommendations: List of recommendations to filter
            mood_analysis: Mood analysis results

        Returns:
            Filtered recommendations that meet mood constraints
        """
        if not mood_analysis.get("target_features"):
            return recommendations

        # Prepare filtering parameters
        filter_params = self._prepare_filtering_parameters(mood_analysis)

        # Apply filtering to each recommendation
        filtered_recommendations = []
        for rec in recommendations:
            if self._should_keep_recommendation(rec, filter_params):
                filtered_recommendations.append(rec)

        self._log_filtering_results(recommendations, filtered_recommendations)
        return filtered_recommendations

    def _prepare_filtering_parameters(self, mood_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters needed for mood-based filtering.

        Args:
            mood_analysis: Mood analysis results

        Returns:
            Dictionary containing filtering parameters
        """
        return {
            "target_features": mood_analysis["target_features"],
            "tolerance_extensions": self._get_tolerance_extensions(),
            "critical_features": ["energy", "acousticness", "instrumentalness", "danceability"]
        }

    def _should_keep_recommendation(
        self,
        recommendation: TrackRecommendation,
        filter_params: Dict[str, Any]
    ) -> bool:
        """Determine if a recommendation should be kept based on mood filtering.

        Args:
            recommendation: Track recommendation to evaluate
            filter_params: Filtering parameters

        Returns:
            True if recommendation should be kept, False if filtered out
        """
        if not recommendation.audio_features:
            # Keep tracks without audio features (will have lower confidence anyway)
            return True

        violations, critical_violations = self._evaluate_feature_violations(
            recommendation,
            filter_params["target_features"],
            filter_params["tolerance_extensions"],
            filter_params["critical_features"]
        )

        return not self._should_filter_recommendation(critical_violations, violations, recommendation)

    def _log_filtering_results(
        self,
        original_recommendations: List[TrackRecommendation],
        filtered_recommendations: List[TrackRecommendation]
    ) -> None:
        """Log the results of mood filtering.

        Args:
            original_recommendations: Original list of recommendations
            filtered_recommendations: Filtered list of recommendations
        """
        logger.info(f"Mood filtering: {len(original_recommendations)} -> {len(filtered_recommendations)} tracks")

    def _get_tolerance_extensions(self) -> Dict[str, Optional[float]]:
        """Get tolerance extensions for different feature types.

        Returns:
            Dictionary mapping feature names to tolerance values
        """
        return {
            # Critical features - moderate extension
            "speechiness": 0.15,  # Extend range by this amount on each side
            "instrumentalness": 0.15,
            # Important features - moderate extension
            "energy": 0.20,
            "valence": 0.25,  # Valence can be more flexible
            "danceability": 0.20,
            # Flexible features
            "tempo": 30.0,
            "loudness": 5.0,
            "acousticness": 0.25,
            "liveness": 0.30,  # Liveness is often not critical
            "mode": None,  # Binary, no tolerance
            "key": None,  # Discrete, no tolerance
            "popularity": 20
        }

    def _evaluate_feature_violations(
        self,
        recommendation: TrackRecommendation,
        target_features: Dict[str, Any],
        tolerance_extensions: Dict[str, Optional[float]],
        critical_features: List[str]
    ) -> tuple[List[str], int]:
        """Evaluate all feature violations for a recommendation.

        Args:
            recommendation: Track recommendation to evaluate
            target_features: Target mood features
            tolerance_extensions: Tolerance configuration
            critical_features: List of critical feature names

        Returns:
            Tuple of (violations_list, critical_violations_count)
        """
        violations = []
        critical_violations = 0

        for feature_name, target_value in target_features.items():
            if feature_name not in recommendation.audio_features:
                continue

            violation_info = self._evaluate_single_feature(
                feature_name,
                target_value,
                recommendation.audio_features[feature_name],
                tolerance_extensions,
                critical_features
            )

            if violation_info:
                violations.append(violation_info["description"])
                if violation_info["is_critical"]:
                    critical_violations += 1

        return violations, critical_violations

    def _evaluate_single_feature(
        self,
        feature_name: str,
        target_value: Any,
        actual_value: float,
        tolerance_extensions: Dict[str, Optional[float]],
        critical_features: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single feature against its target.

        Args:
            feature_name: Name of the feature
            target_value: Target value (range or single value)
            actual_value: Actual value from track
            tolerance_extensions: Tolerance configuration
            critical_features: List of critical feature names

        Returns:
            Violation info dict or None if no violation
        """
        tolerance = tolerance_extensions.get(feature_name)

        # Handle range-based targets (preferred)
        if isinstance(target_value, list) and len(target_value) == 2:
            return self._check_range_violation(
                feature_name, target_value, actual_value, tolerance, critical_features
            )

        # Handle single-value targets
        elif isinstance(target_value, (int, float)):
            return self._check_single_value_violation(
                feature_name, target_value, actual_value, tolerance, critical_features
            )

        return None

    def _check_range_violation(
        self,
        feature_name: str,
        target_range: List[float],
        actual_value: float,
        tolerance: Optional[float],
        critical_features: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Check if a value violates a range-based target.

        Args:
            feature_name: Name of the feature
            target_range: [min, max] target range
            actual_value: Actual value from track
            tolerance: Tolerance extension value
            critical_features: List of critical feature names

        Returns:
            Violation info dict or None if no violation
        """
        min_val, max_val = target_range

        # Extend the range by tolerance on both sides
        if tolerance is not None:
            extended_min = max(0, min_val - tolerance)
            extended_max = min(1 if feature_name != "tempo" else 250, max_val + tolerance)
        else:
            extended_min, extended_max = min_val, max_val

        # Check if value falls within extended range
        if actual_value < extended_min or actual_value > extended_max:
            distance_below = extended_min - actual_value if actual_value < extended_min else 0
            distance_above = actual_value - extended_max if actual_value > extended_max else 0
            distance = max(distance_below, distance_above)

            # Only filter if it's a critical feature and significantly out of range
            is_critical = (
                feature_name in critical_features and
                tolerance is not None and
                distance > tolerance * 2
            )

            return {
                "description": (
                    f"{feature_name}: range=[{min_val:.2f}, {max_val:.2f}], "
                    f"extended=[{extended_min:.2f}, {extended_max:.2f}], "
                    f"actual={actual_value:.2f}, out_by={distance:.2f}"
                ),
                "is_critical": is_critical
            }

        return None

    def _check_single_value_violation(
        self,
        feature_name: str,
        target_value: float,
        actual_value: float,
        tolerance: Optional[float],
        critical_features: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Check if a value violates a single-value target.

        Args:
            feature_name: Name of the feature
            target_value: Target value
            actual_value: Actual value from track
            tolerance: Tolerance value
            critical_features: List of critical feature names

        Returns:
            Violation info dict or None if no violation
        """
        if tolerance is None:
            # Binary or discrete features - skip strict filtering
            if feature_name in ["mode", "key"]:
                return None
            return None

        # Check distance from target
        difference = abs(actual_value - target_value)
        if difference > tolerance:
            # Only filter critical features if very far off
            is_critical = (
                feature_name in critical_features and
                difference > tolerance * 2
            )

            return {
                "description": (
                    f"{feature_name}: target={target_value:.2f}, "
                    f"actual={actual_value:.2f}, diff={difference:.2f}"
                ),
                "is_critical": is_critical
            }

        return None

    def _should_filter_recommendation(
        self,
        critical_violations: int,
        violations: List[str],
        recommendation: TrackRecommendation
    ) -> bool:
        """Determine if a recommendation should be filtered based on violations.

        Args:
            critical_violations: Number of critical violations
            violations: List of all violations
            recommendation: Track recommendation

        Returns:
            True if recommendation should be filtered
        """
        # Only filter if we have 2+ critical violations (very strict filtering)
        if critical_violations >= 2:
            logger.debug(
                f"Filtered out '{recommendation.track_name}' by {', '.join(recommendation.artists)} "
                f"due to {critical_violations} critical violations: {'; '.join(violations)}"
            )
            return True
        else:
            if violations:
                logger.debug(
                    f"Keeping '{recommendation.track_name}' despite violations "
                    f"({critical_violations} critical): {'; '.join(violations[:3])}"
                )
            return False

