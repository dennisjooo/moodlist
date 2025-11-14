"""Playlist target planner for determining playlist size and quality thresholds."""

import random
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
        # Base targets with some randomness to add variety
        base_target = 22
        random_modifier = random.randint(-2, 3)  # -2 to +3 variation

        target_count = base_target + random_modifier
        min_count = 18
        max_count = 28
        quality_threshold = 0.75

        # Analyze mood complexity and specificity
        feature_count = len(target_features)
        high_weight_features = sum(1 for w in mood_analysis.get("feature_weights", {}).values() if w > 0.7)

        # Adjust based on mood specificity
        if feature_count <= 4 or high_weight_features <= 2:
            # Broad mood (e.g., "chill") - more tracks possible
            target_count = 26 + random.randint(-2, 4)  # 24-30 range
            max_count = 32
            quality_threshold = 0.7
            reasoning = "Broad mood allows for larger, more diverse playlist"
        elif feature_count >= 8 or high_weight_features >= 4:
            # Very specific mood (e.g., "super indie acoustic") - still aim for decent size
            target_count = 21 + random.randint(-2, 2)  # 19-23 range
            min_count = 16
            quality_threshold = 0.78
            reasoning = "Specific mood requires focused, high-quality selection"
        else:
            # Moderate specificity
            target_count = 22 + random.randint(-2, 3)  # 20-25 range
            quality_threshold = 0.75
            reasoning = "Balanced target for moderate mood specificity"

        # Check for niche indicators in prompt
        niche_keywords = ["indie", "underground", "obscure", "niche", "rare"]
        if any(keyword in mood_prompt.lower() for keyword in niche_keywords):
            # For niche moods, aim for a good size but be flexible
            target_count = max(20, target_count - random.randint(1, 3))
            min_count = 16
            reasoning += " (niche mood - flexible quality threshold)"

        return {
            "target_count": target_count,
            "min_count": min_count,
            "max_count": max_count,
            "quality_threshold": quality_threshold,
            "reasoning": reasoning
        }