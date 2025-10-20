"""Playlist target planner for determining playlist size and quality thresholds."""

import structlog
from typing import Any, Dict

logger = structlog.get_logger(__name__)


class PlaylistTargetPlanner:
    """Plans playlist target size and quality thresholds based on mood analysis."""

    def __init__(self):
        """Initialize the playlist target planner."""
        pass

    def determine_playlist_target(
        self,
        mood_prompt: str,
        mood_analysis: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine target playlist size and quality thresholds based on mood.

        Args:
            mood_prompt: User's mood description
            mood_analysis: Analyzed mood information
            target_features: Target audio features

        Returns:
            Playlist target plan with size, thresholds, and reasoning
        """
        # Default targets
        target_count = 20
        min_count = 15
        max_count = 25
        quality_threshold = 0.75

        # Analyze mood complexity and specificity
        feature_count = len(target_features)
        high_weight_features = sum(1 for w in mood_analysis.get("feature_weights", {}).values() if w > 0.7)

        # Adjust based on mood specificity
        if feature_count <= 4 or high_weight_features <= 2:
            # Broad mood (e.g., "chill") - more tracks possible
            target_count = 25
            max_count = 30
            quality_threshold = 0.7
            reasoning = "Broad mood allows for larger, more diverse playlist"
        elif feature_count >= 8 or high_weight_features >= 4:
            # Very specific mood (e.g., "super indie acoustic") - fewer, more focused
            target_count = 18
            min_count = 12
            quality_threshold = 0.8
            reasoning = "Specific mood requires focused, high-quality selection"
        else:
            # Moderate specificity
            target_count = 20
            quality_threshold = 0.75
            reasoning = "Balanced target for moderate mood specificity"

        # Check for niche indicators in prompt
        niche_keywords = ["indie", "underground", "obscure", "niche", "rare"]
        if any(keyword in mood_prompt.lower() for keyword in niche_keywords):
            target_count = min(target_count, 20)
            min_count = 12
            reasoning += " (niche mood may have limited matches)"

        return {
            "target_count": target_count,
            "min_count": min_count,
            "max_count": max_count,
            "quality_threshold": quality_threshold,
            "reasoning": reasoning
        }