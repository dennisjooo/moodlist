"""Track filtering and validation utilities."""

import structlog
from typing import Any, Dict, List, Optional

from ....states.agent_state import TrackRecommendation
from ...utils.regional_filter import RegionalFilter
from ...utils.audio_feature_matcher import AudioFeatureMatcher

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

        # Always apply theme exclusions even for recommended artists (e.g., holiday tracks)
        theme_validation = self._validate_theme_compatibility(context)
        if not theme_validation[0]:
            return theme_validation

        # If artist matches and themes are clean, we can skip the heavier checks
        if artist_match[0]:
            return artist_match

        # Check 2: Regional compatibility (language/region must match user intent)
        regional_validation = self._validate_regional_compatibility(context)
        if not regional_validation[0]:
            return regional_validation

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

    def _validate_regional_compatibility(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """Validate that track region/language matches mood intent.

        Respects user's regional preferences - if they ask for Indonesian music,
        allow it. If they don't, block it.

        Args:
            context: Validation context

        Returns:
            (is_valid, reason) - True if region/language compatible
        """
        mood_analysis = context["mood_analysis"]
        preferred_regions = mood_analysis.get("preferred_regions", [])
        excluded_regions = mood_analysis.get("excluded_regions", [])

        # Detect track's region using centralized utility
        track_region = RegionalFilter.detect_track_region(
            track_name=context["track_name"],
            artists=context["artists_lower"]
        )

        # Validate using centralized utility
        return RegionalFilter.validate_regional_compatibility(
            detected_region=track_region,
            preferred_regions=preferred_regions,
            excluded_regions=excluded_regions
        )

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

    def _validate_theme_compatibility(self, context: Dict[str, Any]) -> tuple[bool, str]:
        """Validate that track doesn't contain excluded themes.

        Args:
            context: Validation context

        Returns:
            (is_valid, reason) - True if themes compatible
        """
        mood_analysis = context["mood_analysis"]
        excluded_themes = mood_analysis.get("excluded_themes", [])

        # Use centralized theme filtering
        return RegionalFilter.validate_theme_compatibility(
            track_name=context["track_name"],
            excluded_themes=excluded_themes
        )

    def _filter_and_rank_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None,
        negative_seeds: Optional[List[str]] = None
    ) -> List[TrackRecommendation]:
        """Filter and rank recommendations based on mood analysis.

        Args:
            recommendations: Raw recommendations
            mood_analysis: Mood analysis results
            negative_seeds: Track IDs to explicitly exclude (outliers from previous iterations)

        Returns:
            Filtered and ranked TrackRecommendation objects
        """
        if not recommendations:
            return []

        # CRITICAL: Filter out negative seeds FIRST (before any processing)
        if negative_seeds:
            negative_seeds_set = set(negative_seeds)
            original_count = len(recommendations)
            recommendations = [
                rec for rec in recommendations 
                if rec.get("track_id") not in negative_seeds_set and rec.get("id") not in negative_seeds_set
            ]
            filtered_count = original_count - len(recommendations)
            if filtered_count > 0:
                logger.info(f"✓ Excluded {filtered_count} tracks matching negative seeds")

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
                    user_mentioned_artist=rec_data.get("user_mentioned_artist", False),
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
        # Use centralized violation checking
        return AudioFeatureMatcher.check_feature_violations(
            audio_features=recommendation.audio_features,
            target_features=target_features,
            tolerance_extensions=tolerance_extensions,
            critical_features=critical_features
        )

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
        # Artist discovery tracks are higher quality - be more lenient with filtering
        # (they already passed a 0.3 cohesion threshold vs 0.6 for reccobeat)
        threshold = 3 if recommendation.source == "artist_discovery" else 2

        # Only filter if we exceed the threshold
        if critical_violations >= threshold:
            logger.debug(
                f"Filtered out '{recommendation.track_name}' by {', '.join(recommendation.artists)} "
                f"(source={recommendation.source}) due to {critical_violations} critical violations "
                f"(threshold={threshold}): {'; '.join(violations)}"
            )
            return True
        else:
            if violations:
                logger.debug(
                    f"Keeping '{recommendation.track_name}' despite violations "
                    f"({critical_violations} critical, threshold={threshold}): {'; '.join(violations[:3])}"
                )
            return False
