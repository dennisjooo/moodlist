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
        target_features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Determine target playlist size and quality thresholds based on mood.

        Args:
            mood_prompt: User's mood description
            mood_analysis: Analyzed mood information
            target_features: Target audio features

        Returns:
            Playlist target plan with size, thresholds, and reasoning
        """
        # Base targets centered around ~20 tracks with natural variation
        base_target = 20
        random_modifier = random.randint(-3, 3)  # -3 to +3 variation for more diversity

        target_count = base_target + random_modifier
        min_count = 16
        quality_threshold = 0.75

        # Analyze mood complexity and specificity
        feature_count = len(target_features)
        high_weight_features = sum(
            1 for w in mood_analysis.get("feature_weights", {}).values() if w > 0.7
        )

        # Adjust based on mood specificity
        if feature_count <= 4 or high_weight_features <= 2:
            # Broad mood (e.g., "chill") - slightly larger variation
            target_count = 22 + random.randint(-3, 3)  # 19-25 range
            quality_threshold = 0.7
            reasoning = "Broad mood allows for diverse selection"
        elif feature_count >= 8 or high_weight_features >= 4:
            # Very specific mood - focused selection
            target_count = 19 + random.randint(-2, 2)  # 17-21 range
            min_count = 16
            quality_threshold = 0.78
            reasoning = "Specific mood requires focused, high-quality selection"
        else:
            # Moderate specificity
            target_count = 20 + random.randint(-3, 3)  # 17-23 range
            quality_threshold = 0.75
            reasoning = "Balanced target for moderate mood specificity"

        # Check for niche indicators in prompt
        niche_keywords = ["indie", "underground", "obscure", "niche", "rare"]
        if any(keyword in mood_prompt.lower() for keyword in niche_keywords):
            # For niche moods, slightly smaller
            target_count = max(17, target_count - random.randint(0, 2))
            min_count = 15
            reasoning += " (niche mood - focused selection)"

        return {
            "target_count": target_count,
            "min_count": min_count,
            "quality_threshold": quality_threshold,
            "reasoning": reasoning,
        }
