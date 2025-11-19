"""Fallback intent analysis using rule-based approach."""

import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)


class IntentFallbackAnalyzer:
    """Provides fallback intent analysis when LLM is unavailable."""

    @staticmethod
    def analyze_intent_fallback(mood_prompt: str) -> Dict[str, Any]:
        """Fallback intent analysis using rule-based approach.

        Args:
            mood_prompt: User's mood description

        Returns:
            Basic intent analysis dictionary
        """
        mood_lower = mood_prompt.lower()

        # Determine intent type based on keywords
        intent_type = "mood_variety"  # Default

        if any(
            phrase in mood_lower for phrase in ["like ", "similar to", "things like"]
        ):
            intent_type = "specific_track_similar"
        elif any(phrase in mood_lower for phrase in ["playlist", "give me", "only"]):
            intent_type = "artist_focus"
        elif any(
            word in mood_lower for word in ["explore", "discover", "variety", "mix"]
        ):
            intent_type = "genre_exploration"

        # Basic genre detection
        primary_genre = IntentFallbackAnalyzer._detect_genre(mood_lower)

        # Set genre strictness
        genre_strictness = 0.6  # Default moderate
        if intent_type in ["artist_focus", "specific_track_similar"]:
            genre_strictness = 0.85  # Stricter for specific requests
        elif intent_type == "genre_exploration":
            genre_strictness = 0.7

        # Default values
        intent_data = {
            "intent_type": intent_type,
            "user_mentioned_tracks": [],
            "user_mentioned_artists": [],
            "primary_genre": primary_genre,
            "genre_strictness": genre_strictness,
            "language_preferences": ["english"],
            "exclude_regions": [],
            "allow_obscure_artists": False,
            "quality_threshold": 0.6,
            "reasoning": "Fallback rule-based analysis",
        }

        logger.info(f"Fallback intent analysis: {intent_type}, genre: {primary_genre}")

        return intent_data

    @staticmethod
    def _detect_genre(mood_lower: str) -> str:
        """Detect genre from mood description.

        Args:
            mood_lower: Lowercased mood prompt

        Returns:
            Detected genre or None
        """
        genre_keywords = {
            "trap": ["trap", "travis scott", "future", "migos"],
            "hip hop": ["hip hop", "rap", "rapper"],
            "pop": ["pop", "taylor swift", "ariana"],
            "rock": ["rock", "indie", "alternative"],
            "electronic": ["electronic", "edm", "techno", "house"],
            "jazz": ["jazz", "bebop", "swing"],
            "classical": ["classical", "orchestra", "symphony"],
            "country": ["country", "nashville"],
            "funk": ["funk", "funky"],
            "soul": ["soul", "r&b", "rnb"],
        }

        for genre, keywords in genre_keywords.items():
            if any(keyword in mood_lower for keyword in keywords):
                return genre

        return None
