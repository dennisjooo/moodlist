"""Intent data validation logic."""

import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)


class IntentValidator:
    """Validates and sanitizes intent data."""

    @staticmethod
    def validate_intent_data(intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize intent data from LLM.

        Args:
            intent_data: Raw intent data from LLM

        Returns:
            Validated intent data
        """
        # Ensure intent_type is valid
        valid_intent_types = [
            "artist_focus",
            "genre_exploration",
            "mood_variety",
            "specific_track_similar",
        ]
        if intent_data.get("intent_type") not in valid_intent_types:
            logger.warning(
                f"Invalid intent_type '{intent_data.get('intent_type')}', defaulting to 'mood_variety'"
            )
            intent_data["intent_type"] = "mood_variety"

        # Ensure arrays exist
        if not isinstance(intent_data.get("user_mentioned_tracks"), list):
            intent_data["user_mentioned_tracks"] = []
        if not isinstance(intent_data.get("user_mentioned_artists"), list):
            intent_data["user_mentioned_artists"] = []
        if not isinstance(intent_data.get("language_preferences"), list):
            intent_data["language_preferences"] = ["english"]
        if not isinstance(intent_data.get("exclude_regions"), list):
            intent_data["exclude_regions"] = []

        # Validate numeric ranges
        if not isinstance(intent_data.get("genre_strictness"), (int, float)):
            intent_data["genre_strictness"] = 0.6
        else:
            intent_data["genre_strictness"] = max(
                0.0, min(1.0, float(intent_data["genre_strictness"]))
            )

        if not isinstance(intent_data.get("quality_threshold"), (int, float)):
            intent_data["quality_threshold"] = 0.6
        else:
            intent_data["quality_threshold"] = max(
                0.0, min(1.0, float(intent_data["quality_threshold"]))
            )

        # Ensure boolean
        if not isinstance(intent_data.get("allow_obscure_artists"), bool):
            intent_data["allow_obscure_artists"] = False

        # Validate track mentions structure
        validated_tracks = []
        for track in intent_data.get("user_mentioned_tracks", []):
            if (
                isinstance(track, dict)
                and track.get("track_name")
                and track.get("artist_name")
            ):
                validated_tracks.append(
                    {
                        "track_name": str(track["track_name"]),
                        "artist_name": str(track["artist_name"]),
                        "priority": track.get("priority", "medium")
                        if track.get("priority") in ["high", "medium"]
                        else "medium",
                    }
                )
        intent_data["user_mentioned_tracks"] = validated_tracks

        return intent_data
