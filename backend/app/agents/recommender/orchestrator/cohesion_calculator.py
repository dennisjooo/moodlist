"""Cohesion calculator for evaluating track cohesion against target mood."""

import structlog
from typing import Any, Dict, List, Optional

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class CohesionCalculator:
    """Calculates cohesion scores and identifies outlier tracks."""

    def __init__(self):
        """Initialize the cohesion calculator."""
        pass

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
        feature_weights = feature_weights or self.get_default_feature_weights()
        tolerance_thresholds = self.get_tolerance_thresholds()
        critical_features = self.get_critical_features(feature_weights)

        # Calculate cohesion for each track
        track_scores = {}
        for rec in recommendations:
            track_scores[rec.track_id] = self.calculate_track_cohesion(
                rec, target_features, feature_weights, tolerance_thresholds
            )

        # Detect outliers and calculate overall cohesion
        outliers, cohesion_scores = self.detect_outliers(
            recommendations, track_scores, critical_features
        )

        overall_cohesion = self.calculate_overall_cohesion(cohesion_scores)

        return {
            "score": overall_cohesion,
            "outliers": outliers,
            "track_scores": track_scores
        }

    def get_default_feature_weights(self) -> Dict[str, float]:
        """Get default feature weights for cohesion calculation."""
        return {
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

    def get_tolerance_thresholds(self) -> Dict[str, float]:
        """Get tolerance thresholds for cohesion checking."""
        return {
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

    def get_critical_features(self, feature_weights: Dict[str, float]) -> List[str]:
        """Get list of critical features based on high weights."""
        return [
            feature for feature, weight in feature_weights.items()
            if weight > 0.65
        ]

    def calculate_track_cohesion(
        self,
        track: TrackRecommendation,
        target_features: Dict[str, Any],
        feature_weights: Dict[str, float],
        tolerance_thresholds: Dict[str, float]
    ) -> float:
        """Calculate cohesion score for a single track.

        Args:
            track: Track recommendation to evaluate
            target_features: Target audio features from mood analysis
            feature_weights: Feature importance weights
            tolerance_thresholds: Tolerance thresholds for each feature

        Returns:
            Cohesion score for the track (0-1)
        """
        # IMPORTANT: RecoBeat tracks are biased - they were GENERATED using these target features
        # So they'll naturally score higher on cohesion even if they're garbage (circular dependency)
        # Artist tracks are from Spotify's curated top tracks, more trustworthy
        is_reccobeat = track.source == "reccobeat"

        if not track.audio_features:
            # Artist tracks without features get higher default (curated by Spotify)
            # RecoBeat tracks without features get lower default (less trustworthy)
            return 0.65 if is_reccobeat else 0.75

        violations = []
        weighted_violations = 0.0
        weighted_matches = []

        for feature_name, target_value in target_features.items():
            if feature_name not in track.audio_features:
                continue

            actual_value = track.audio_features[feature_name]
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

        return track_cohesion

    def detect_outliers(
        self,
        recommendations: List[TrackRecommendation],
        track_scores: Dict[str, float],
        critical_features: List[str]
    ) -> tuple[List[str], List[float]]:
        """Detect outlier tracks based on cohesion scores and violations.

        Args:
            recommendations: List of track recommendations
            track_scores: Pre-calculated cohesion scores for each track
            critical_features: List of critical feature names

        Returns:
            Tuple of (outlier_track_ids, valid_cohesion_scores)
        """
        outliers = []
        cohesion_scores = []

        for rec in recommendations:
            # CRITICAL: Skip quality evaluation for protected tracks (user-mentioned anchors)
            if rec.protected or rec.user_mentioned:
                logger.info(
                    f"Skipping outlier detection for protected track: {rec.track_name} by {', '.join(rec.artists)} "
                    f"(user_mentioned={rec.user_mentioned}, anchor_type={rec.anchor_type})"
                )
                # Include in cohesion scores with perfect score (don't penalize playlist)
                cohesion_scores.append(1.0)
                continue
            
            track_cohesion = track_scores[rec.track_id]
            is_reccobeat = rec.source == "reccobeat"

            # Mark as outlier based on weighted violations and cohesion score
            # STRICTER for RecoBeat (circular dependency bias), RELAXED for artist tracks
            if is_reccobeat:
                # RecoBeat: stricter outlier detection (they're biased to match features)
                # Outlier if: high weighted violations (>1.2) OR critical feature + moderate cohesion
                if track_cohesion < 0.6:  # Simplified for now - could be enhanced
                    outliers.append(rec.track_id)
                    logger.debug(
                        f"Outlier detected (RecoBeat): {rec.track_name} by {', '.join(rec.artists)} "
                        f"(score={track_cohesion:.2f})"
                    )
                else:
                    cohesion_scores.append(track_cohesion)
            else:
                # Artist tracks: relaxed outlier detection (curated by Spotify, more trustworthy)
                # Outlier only if: very low cohesion
                if track_cohesion < 0.4:
                    outliers.append(rec.track_id)
                    logger.debug(
                        f"Outlier detected (Artist): {rec.track_name} by {', '.join(rec.artists)} "
                        f"(score={track_cohesion:.2f})"
                    )
                else:
                    cohesion_scores.append(track_cohesion)

        return outliers, cohesion_scores

    def calculate_overall_cohesion(self, cohesion_scores: List[float]) -> float:
        """Calculate overall cohesion score from individual track scores.

        Args:
            cohesion_scores: List of cohesion scores for valid tracks

        Returns:
            Overall cohesion score (0-1)
        """
        if cohesion_scores:
            return sum(cohesion_scores) / len(cohesion_scores)
        else:
            return 0.0

    def extract_llm_outliers(
        self,
        specific_concerns: List[str],
        recommendations: List[TrackRecommendation]
    ) -> List[str]:
        """Extract track IDs from LLM's specific concerns.
        
        LLM provides concerns in format: "Track Name by Artist Name feels out of place because..."
        We need to match these to actual track IDs in recommendations.
        
        Args:
            specific_concerns: List of LLM concern strings
            recommendations: List of current track recommendations
            
        Returns:
            List of track IDs identified as outliers by LLM
        """
        if not specific_concerns:
            return []
        
        outlier_track_ids = []
        
        for concern in specific_concerns:
            # Extract track name from concern (format: "Track Name by Artist Name feels...")
            # Split on " by " to get track name
            if " by " not in concern:
                continue
            
            track_name_part = concern.split(" by ")[0].strip()
            
            # Match against recommendations (case-insensitive, partial match for robustness)
            for rec in recommendations:
                # CRITICAL: Skip protected tracks (user-mentioned anchors)
                if rec.protected or rec.user_mentioned:
                    if rec.track_name.lower() == track_name_part.lower() or track_name_part.lower() in rec.track_name.lower():
                        logger.warning(
                            f"LLM tried to flag protected track as outlier: {rec.track_name} by {', '.join(rec.artists)} "
                            f"(user_mentioned={rec.user_mentioned}) - IGNORING LLM suggestion"
                        )
                    continue
                
                # Exact match (case-insensitive)
                if rec.track_name.lower() == track_name_part.lower():
                    outlier_track_ids.append(rec.track_id)
                    logger.info(
                        f"LLM flagged outlier: {rec.track_name} by {', '.join(rec.artists)} "
                        f"(matched from concern: {concern[:80]}...)"
                    )
                    break
                # Partial match as fallback (track name is substring)
                elif track_name_part.lower() in rec.track_name.lower():
                    outlier_track_ids.append(rec.track_id)
                    logger.info(
                        f"LLM flagged outlier (partial match): {rec.track_name} by {', '.join(rec.artists)} "
                        f"(matched '{track_name_part}' from concern)"
                    )
                    break
        
        return outlier_track_ids