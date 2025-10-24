"""Track filtering and validation utilities."""

import structlog
from typing import Any, Dict, List, Optional

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


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
        if not mood_analysis:
            return (True, "No mood analysis available")

        # Prepare validation context
        context = self._prepare_validation_context(track_name, artists, mood_analysis)

        # Check 1: Artist matching (always accept if artist matches)
        artist_match = self._check_artist_match(context)
        if artist_match[0]:
            return artist_match

        # Check 2: Language compatibility
        language_validation = self._validate_language_compatibility(context)
        if not language_validation[0]:
            return language_validation

        # Check 3: Genre compatibility
        genre_validation = self._validate_genre_compatibility(context)
        if not genre_validation[0]:
            return genre_validation

        # If we got here, no obvious red flags
        return (True, "No obvious mismatches detected")

    def _prepare_validation_context(
        self,
        track_name: str,
        artists: List[str],
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

    def _check_artist_match(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """Check if any track artist matches the recommended artists.

        Args:
            context: Validation context

        Returns:
            (is_valid, reason) - True if artist matches
        """
        for artist in context["artists_lower"]:
            if any(rec_artist in artist or artist in rec_artist for rec_artist in context["artist_recs_lower"]):
                return (True, "Artist matches mood recommendations")
        return (False, "")

    def _validate_language_compatibility(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """Validate that track language is compatible with mood language.

        Args:
            context: Validation context

        Returns:
            (is_valid, reason) - True if language compatible
        """
        mood_language = self._detect_mood_language(context["all_keywords"])
        if not mood_language:
            return (True, "No specific mood language detected")

        language_indicators = self._get_language_indicators()

        for lang, indicators in language_indicators.items():
            if lang == mood_language:
                continue  # Skip checking against the mood's own language

            # Check string indicators
            for indicator in indicators:
                if isinstance(indicator, str):
                    if indicator in context["track_and_artists"]:
                        return (False, f"Language mismatch: track appears to be {lang}, mood is {mood_language}")
                else:
                    # Unicode range check for CJK languages
                    for char in context["track_name"]:
                        if indicator <= char <= indicators[indicators.index(indicator) + 1]:
                            return (False, f"Language mismatch: track appears to be {lang}, mood is {mood_language}")

        return (True, "Language compatible")

    def _detect_mood_language(self, keywords: List[str]) -> Optional[str]:
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

    def _get_language_indicators(self) -> Dict[str, List[Any]]:
        """Get language detection indicators.

        Returns:
            Dictionary mapping languages to indicator lists
        """
        return {
            "spanish": ["el ", "la ", "los ", "las ", "mi ", "tu ", "de ", "con ", "por ", "para "],
            "korean": ["\u3131", "\u314f", "\uac00", "\ud7a3"],  # Hangul character ranges
            "japanese": ["\u3040", "\u309f", "\u30a0", "\u30ff"],  # Hiragana/Katakana
            "chinese": ["\u4e00", "\u9fff"],  # Common CJK
            "portuguese": ["meu ", "minha ", "você ", "está ", "muito ", "bem "],
            "german": ["der ", "die ", "das ", "ich ", "du ", "und ", "mit "],
            "french": ["le ", "la ", "les ", "de ", "je ", "tu ", "avec ", "pour "]
        }

    def _validate_genre_compatibility(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """Validate that track genres are compatible with mood genres.

        Args:
            context: Validation context

        Returns:
            (is_valid, reason) - True if genres compatible
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
                    return (False, f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}")

                # Check reverse
                has_group1_mood = any(g in mood_genres for g in group1)
                has_group2_track = any(g in track_genres for g in group2)
                if has_group1_mood and has_group2_track:
                    return (False, f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}")

        return (True, "Genres compatible")

    def _filter_and_rank_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None
    ) -> List[TrackRecommendation]:
        """Filter and rank recommendations based on mood analysis.

        Args:
            recommendations: Raw recommendations
            mood_analysis: Mood analysis results

        Returns:
            Filtered and ranked TrackRecommendation objects
        """
        if not recommendations:
            return []

        # Convert to TrackRecommendation objects
        rec_objects = []
        for rec_data in recommendations:
            try:
                # Handle both 'track_id' and 'id' fields for compatibility
                track_id = rec_data.get("track_id") or rec_data.get("id", "")
                if not track_id:
                    logger.warning("Skipping recommendation without track ID")
                    continue

                rec_obj = TrackRecommendation(
                    track_id=track_id,
                    track_name=rec_data.get("track_name", "Unknown Track"),
                    artists=rec_data.get("artists", ["Unknown Artist"]),
                    spotify_uri=rec_data.get("spotify_uri"),
                    confidence_score=rec_data.get("confidence_score", 0.5),
                    audio_features=rec_data.get("audio_features"),
                    reasoning=rec_data.get("reasoning", "Mood-based recommendation"),
                    source=rec_data.get("source", "reccobeat"),
                    user_mentioned=rec_data.get("user_mentioned", False),
                    anchor_type=rec_data.get("anchor_type"),
                    protected=rec_data.get("protected", False)
                )
                rec_objects.append(rec_obj)

            except Exception as e:
                logger.warning(f"Failed to create recommendation object: {e}")
                continue

        # Sort by confidence score before filtering
        rec_objects.sort(key=lambda x: x.confidence_score, reverse=True)

        # Apply mood-based filtering if available
        if mood_analysis and mood_analysis.get("target_features"):
            rec_objects = self._apply_mood_filtering(rec_objects, mood_analysis)

        return rec_objects

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

        target_features = mood_analysis["target_features"]
        filtered_recommendations = []

        tolerance_extensions = self._get_tolerance_extensions()
        critical_features = ["energy", "acousticness", "instrumentalness", "danceability"]

        for rec in recommendations:
            if not rec.audio_features:
                # Keep tracks without audio features (will have lower confidence anyway)
                filtered_recommendations.append(rec)
                continue

            violations, critical_violations = self._evaluate_feature_violations(
                rec, target_features, tolerance_extensions, critical_features
            )

            if self._should_filter_recommendation(critical_violations, violations, rec):
                continue

            filtered_recommendations.append(rec)

        logger.info(f"Mood filtering: {len(recommendations)} -> {len(filtered_recommendations)} tracks")
        return filtered_recommendations

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
