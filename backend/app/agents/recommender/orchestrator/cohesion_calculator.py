"""Cohesion calculator for evaluating track cohesion against target mood."""

import structlog
from typing import Any, Dict, List, Optional

from ...states.agent_state import TrackRecommendation
from ..utils.audio_feature_matcher import AudioFeatureMatcher

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
            tolerance_thresholds: Tolerance thresholds for each feature (IGNORED - using centralized)

        Returns:
            Cohesion score for the track (0-1)
        """
        # Use centralized cohesion calculation with base tolerances
        # NOTE: tolerance_thresholds parameter is kept for backwards compatibility but not used
        return AudioFeatureMatcher.calculate_cohesion(
            audio_features=track.audio_features,
            target_features=target_features,
            feature_weights=feature_weights,
            source=track.source,
            tolerance_mode="base"
        )

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
            if rec.protected or rec.user_mentioned or rec.user_mentioned_artist:
                logger.info(
                    f"Skipping outlier detection for protected track: {rec.track_name} by {', '.join(rec.artists)} "
                    f"(user_mentioned={rec.user_mentioned}, user_mentioned_artist={rec.user_mentioned_artist}, anchor_type={rec.anchor_type})"
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
                # Outlier only if: extremely low cohesion (let LLM handle cultural/genre mismatches)
                if track_cohesion < 0.3:
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