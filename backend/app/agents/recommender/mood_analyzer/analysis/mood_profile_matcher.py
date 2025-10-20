"""Mood profile matching for rule-based mood analysis."""

from typing import Any, Dict, List, Tuple

from ..config import MOOD_PROFILES


class MoodProfileMatcher:
    """Handles matching mood prompts to predefined mood profiles."""

    def __init__(self):
        """Initialize the mood profile matcher."""
        pass

    def match_mood_profiles(self, mood_prompt: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Match mood prompt against predefined mood profiles.

        Args:
            mood_prompt: User's mood description

        Returns:
            List of (mood_name, profile) tuples that match the prompt
        """
        prompt_lower = mood_prompt.lower()
        matched_profiles = []

        for mood_name, profile in MOOD_PROFILES.items():
            if any(keyword in prompt_lower for keyword in profile["keywords"]):
                matched_profiles.append((mood_name, profile))

        return matched_profiles

    def apply_mood_profiles(
        self,
        matched_profiles: List[Tuple[str, Dict[str, Any]]],
        mood_prompt: str,
        analysis: Dict[str, Any]
    ) -> None:
        """Apply matched mood profiles to the analysis result.

        Args:
            matched_profiles: List of (mood_name, profile) tuples
            mood_prompt: Original mood prompt for context
            analysis: Analysis dictionary to update
        """
        if not matched_profiles:
            return

        for mood_name, profile in matched_profiles:
            # Update mood interpretation
            analysis["mood_interpretation"] = f"{mood_name.capitalize()} mood based on: {mood_prompt}"

            # Merge target features
            analysis["target_features"].update(profile["features"])

            # Merge feature weights
            analysis["feature_weights"].update(profile["weights"])

            # Update primary emotion
            analysis["primary_emotion"] = profile.get("emotion", "neutral")

    def get_profile_emotion(self, mood_name: str) -> str:
        """Get the emotion associated with a mood profile.

        Args:
            mood_name: Name of the mood profile

        Returns:
            Emotion string (positive, negative, neutral)
        """
        profile = MOOD_PROFILES.get(mood_name, {})
        return profile.get("emotion", "neutral")
