"""Validation utilities for track recommendations."""

import logging
from typing import Any, Dict, Optional, Tuple

from ..utils import config

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, is_valid: bool, reason: str = ""):
        """Initialize validation result.

        Args:
            is_valid: Whether the validation passed
            reason: Reason for validation failure (if applicable)
        """
        self.is_valid = is_valid
        self.reason = reason

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context."""
        return self.is_valid


class RecommendationValidator:
    """Handles validation of track recommendations against mood criteria."""

    @staticmethod
    def validate_track_relevance(
        track_name: str,
        artists: list,
        mood_analysis: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """Validate if a track is relevant to the mood before accepting.

        Filters out obvious mismatches (wrong language, genre, etc.)

        Args:
            track_name: Track name to validate
            artists: List of artist names
            mood_analysis: Mood analysis with artist recommendations and keywords

        Returns:
            ValidationResult indicating if track is relevant and why
        """
        if not mood_analysis:
            return ValidationResult(True, "No mood analysis available")

        # Prepare validation context
        context = RecommendationValidator._prepare_validation_context(track_name, artists, mood_analysis)

        # Check 1: Artist matching (always accept if artist matches)
        artist_match = RecommendationValidator._check_artist_match(context)
        if artist_match.is_valid:
            return artist_match

        # Check 2: Language compatibility
        language_validation = RecommendationValidator._validate_language_compatibility(context)
        if not language_validation.is_valid:
            return language_validation

        # Check 3: Genre compatibility
        genre_validation = RecommendationValidator._validate_genre_compatibility(context)
        if not genre_validation.is_valid:
            return genre_validation

        # If we got here, no obvious red flags
        return ValidationResult(True, "No obvious mismatches detected")

    @staticmethod
    def _prepare_validation_context(
        track_name: str,
        artists: list,
        mood_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context data for validation checks.

        Args:
            track_name: Track name
            artists: List of artist names
            mood_analysis: Mood analysis data

        Returns:
            Context dictionary with normalized data
        """
        # Get mood context
        artist_recommendations = mood_analysis.get("artist_recommendations", [])
        genre_keywords = mood_analysis.get("genre_keywords", [])
        search_keywords = mood_analysis.get("search_keywords", [])

        # Normalize for comparison
        track_lower = track_name.lower()
        artists_lower = [a.lower() for a in artists]
        artist_recs_lower = [a.lower() for a in artist_recommendations]
        all_keywords = genre_keywords + search_keywords
        track_and_artists = track_lower + " " + " ".join(artists_lower)

        return {
            "track_name": track_name,
            "track_lower": track_lower,
            "artists_lower": artists_lower,
            "artist_recs_lower": artist_recs_lower,
            "all_keywords": all_keywords,
            "track_and_artists": track_and_artists,
            "mood_analysis": mood_analysis
        }

    @staticmethod
    def _check_artist_match(context: Dict[str, Any]) -> ValidationResult:
        """Check if any track artist matches the recommended artists.

        Args:
            context: Validation context

        Returns:
            ValidationResult indicating if artist matches
        """
        for artist in context["artists_lower"]:
            if any(rec_artist in artist or artist in rec_artist for rec_artist in context["artist_recs_lower"]):
                return ValidationResult(True, "Artist matches mood recommendations")
        return ValidationResult(False, "")

    @staticmethod
    def _validate_language_compatibility(context: Dict[str, Any]) -> ValidationResult:
        """Validate that track language is compatible with mood language.

        Args:
            context: Validation context

        Returns:
            ValidationResult indicating if language is compatible
        """
        mood_language = RecommendationValidator._detect_mood_language(context["all_keywords"])
        if not mood_language:
            return ValidationResult(True, "No specific mood language detected")

        language_indicators = config.language_indicators

        for lang, indicators in language_indicators.items():
            if lang == mood_language:
                continue  # Skip checking against the mood's own language

            # Check string indicators
            for indicator in indicators:
                if isinstance(indicator, str):
                    if indicator in context["track_and_artists"]:
                        return ValidationResult(
                            False,
                            f"Language mismatch: track appears to be {lang}, mood is {mood_language}"
                        )
                else:
                    # Unicode range check for CJK languages
                    for char in context["track_name"]:
                        if indicator <= char <= language_indicators[lang][language_indicators[lang].index(indicator) + 1]:
                            return ValidationResult(
                                False,
                                f"Language mismatch: track appears to be {lang}, mood is {mood_language}"
                            )

        return ValidationResult(True, "Language compatible")

    @staticmethod
    def _detect_mood_language(keywords: list) -> Optional[str]:
        """Detect the language represented by mood keywords.

        Args:
            keywords: List of mood keywords

        Returns:
            Detected language or None
        """
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if any(lang_word in keyword_lower for lang_word in ["french", "français"]):
                return "french"
            elif any(lang_word in keyword_lower for lang_word in ["spanish", "latin", "latino"]):
                return "spanish"
            elif any(lang_word in keyword_lower for lang_word in ["korean", "k-pop", "kpop"]):
                return "korean"
            elif any(lang_word in keyword_lower for lang_word in ["japanese", "j-pop", "jpop", "city pop"]):
                return "japanese"
            elif any(lang_word in keyword_lower for lang_word in ["portuguese", "brazilian", "bossa"]):
                return "portuguese"
        return None

    @staticmethod
    def _validate_genre_compatibility(context: Dict[str, Any]) -> ValidationResult:
        """Validate that track genres are compatible with mood genres.

        Args:
            context: Validation context

        Returns:
            ValidationResult indicating if genres are compatible
        """
        genre_terms = ["funk", "disco", "house", "techno", "jazz", "rock", "pop", "indie",
                       "electronic", "hip hop", "rap", "soul", "blues", "metal", "punk",
                       "reggae", "country", "folk", "classical", "ambient", "trap"]

        track_genres = []
        mood_genres = []

        # Find genres in track/artist
        for term in genre_terms:
            if term in context["track_and_artists"]:
                track_genres.append(term)

        # Find genres in mood keywords
        for keyword in context["all_keywords"]:
            keyword_lower = keyword.lower()
            for term in genre_terms:
                if term in keyword_lower:
                    mood_genres.append(term)

        # If both have genre indicators and they don't overlap at all, flag it
        if track_genres and mood_genres:
            # Check for conflicting genres (e.g., "hip hop" for "indie rock")
            conflicting_pairs = [
                (["classical", "jazz", "blues"], ["metal", "punk", "trap"]),
                (["folk", "country", "indie"], ["electronic", "techno", "house"]),
                (["hip hop", "rap", "trap"], ["rock", "indie", "folk"])
            ]

            for group1, group2 in conflicting_pairs:
                has_group1 = any(g in track_genres for g in group1)
                has_group2 = any(g in mood_genres for g in group2)
                if has_group1 and has_group2:
                    return ValidationResult(
                        False,
                        f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}"
                    )

                # Check reverse
                has_group1_mood = any(g in mood_genres for g in group1)
                has_group2_track = any(g in track_genres for g in group2)
                if has_group1_mood and has_group2_track:
                    return ValidationResult(
                        False,
                        f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}"
                    )

        return ValidationResult(True, "Genres compatible")
