"""Centralized audio feature matching and cohesion calculation utilities."""

from typing import Any, Dict, List, Optional, Tuple


class AudioFeatureMatcher:
    """Handles audio feature matching, cohesion scoring, and violation detection."""

    # Centralized tolerance thresholds for audio features
    # These define how much a feature can deviate from target before being flagged
    BASE_TOLERANCE_THRESHOLDS = {
        "energy": 0.25,  # ±0.25 (stricter - energy is important)
        "valence": 0.30,  # ±0.30 (moderate - mood flexibility)
        "danceability": 0.30,  # ±0.30 (moderate)
        "acousticness": 0.40,  # ±0.40 (flexible - can vary)
        "instrumentalness": 0.25,  # ±0.25 (stricter - vocal presence matters)
        "speechiness": 0.25,  # ±0.25 (stricter - avoid podcasts)
        "tempo": 35.0,  # ±35 BPM (moderate)
        "loudness": 6.0,  # ±6 dB (moderate)
        "liveness": 0.40,  # ±0.40 (flexible - usually not critical)
        "popularity": 30,  # ±30 points (flexible)
    }

    # Extended tolerances for more lenient matching (used in track filtering)
    EXTENDED_TOLERANCE_THRESHOLDS = {
        "energy": 0.20,  # Extension amount
        "valence": 0.25,
        "danceability": 0.20,
        "acousticness": 0.25,
        "instrumentalness": 0.15,
        "speechiness": 0.15,
        "tempo": 30.0,
        "loudness": 5.0,
        "liveness": 0.30,
        "popularity": 20,
    }

    # Relaxed tolerances for artist discovery (more lenient to get enough tracks)
    RELAXED_TOLERANCE_THRESHOLDS = {
        "energy": 0.35,
        "valence": 0.35,
        "danceability": 0.35,
        "acousticness": 0.45,
        "instrumentalness": 0.30,
        "speechiness": 0.30,
        "tempo": 45.0,
        "loudness": 7.0,
        "liveness": 0.45,
        "popularity": 35,
    }

    @classmethod
    def calculate_cohesion(
        cls,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any],
        feature_weights: Optional[Dict[str, float]] = None,
        source: Optional[str] = None,
        tolerance_mode: str = "base",
    ) -> float:
        """Calculate cohesion score between audio features and target mood features.

        Args:
            audio_features: Track's audio features from Spotify/RecoBeat
            target_features: Target mood features from mood analysis
            feature_weights: Optional weights for each feature (0-1). If None, uses equal weights
            source: Optional source identifier ("reccobeat", "artist_discovery", etc.)
            tolerance_mode: Which tolerance set to use ("base", "relaxed", "extended")

        Returns:
            Cohesion score (0-1), where 1 = perfect match, 0 = poor match
        """
        if not audio_features or not target_features:
            # Default scores based on source reliability
            if source == "reccobeat":
                return 0.65  # RecoBeat without features = moderate trust
            elif source == "artist_discovery":
                return 0.75  # Artist tracks without features = higher trust (curated)
            else:
                return 0.70  # Unknown source = neutral

        # Get appropriate tolerance thresholds
        tolerance_thresholds = cls._get_tolerance_thresholds(tolerance_mode)

        weighted_matches = []

        for feature_name, target_value in target_features.items():
            if feature_name not in audio_features:
                continue

            actual_value = audio_features[feature_name]
            tolerance = tolerance_thresholds.get(feature_name)

            if tolerance is None:
                continue  # Skip features without defined tolerance

            # Get weight for this feature (default to 0.5 if not specified)
            weight = feature_weights.get(feature_name, 0.5) if feature_weights else 1.0

            # Convert target value to single number if it's a range
            if isinstance(target_value, list) and len(target_value) == 2:
                target_single = sum(target_value) / 2
            elif isinstance(target_value, (int, float)):
                target_single = float(target_value)
            else:
                continue  # Skip invalid target values

            # Calculate difference and match score
            difference = abs(actual_value - target_single)
            match_score = max(0.0, 1.0 - (difference / tolerance))

            weighted_matches.append((match_score, weight))

        # Calculate weighted average cohesion score
        if weighted_matches:
            if feature_weights:
                # Weighted mode
                total_weight = sum(w for _, w in weighted_matches)
                weighted_sum = sum(score * w for score, w in weighted_matches)
                cohesion = weighted_sum / total_weight if total_weight > 0 else 0.0
            else:
                # Unweighted mode (simple average)
                cohesion = sum(score for score, _ in weighted_matches) / len(
                    weighted_matches
                )
        else:
            cohesion = 0.70  # Neutral score if no features to compare

        return cohesion

    @classmethod
    def check_feature_violations(
        cls,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any],
        tolerance_extensions: Optional[Dict[str, float]] = None,
        critical_features: Optional[List[str]] = None,
    ) -> Tuple[List[str], int]:
        """Check for feature violations (values outside acceptable ranges).

        Args:
            audio_features: Track's audio features
            target_features: Target mood features (can be ranges or single values)
            tolerance_extensions: Optional extensions to base tolerances
            critical_features: List of features considered critical (violations penalized more)

        Returns:
            Tuple of (violations_list, critical_violations_count)
        """
        violations = []
        critical_violations = 0

        critical_features = critical_features or [
            "energy",
            "acousticness",
            "instrumentalness",
            "danceability",
        ]
        tolerance_extensions = tolerance_extensions or {}

        for feature_name, target_value in target_features.items():
            if feature_name not in audio_features:
                continue

            actual_value = audio_features[feature_name]

            # Handle range-based targets
            if isinstance(target_value, list) and len(target_value) == 2:
                violation_info = cls._check_range_violation(
                    feature_name,
                    target_value,
                    actual_value,
                    tolerance_extensions.get(feature_name),
                    critical_features,
                )
            # Handle single-value targets
            elif isinstance(target_value, (int, float)):
                violation_info = cls._check_single_value_violation(
                    feature_name,
                    target_value,
                    actual_value,
                    tolerance_extensions.get(feature_name),
                    critical_features,
                )
            else:
                continue

            if violation_info:
                violations.append(violation_info["description"])
                if violation_info["is_critical"]:
                    critical_violations += 1

        return violations, critical_violations

    @classmethod
    def _check_range_violation(
        cls,
        feature_name: str,
        target_range: List[float],
        actual_value: float,
        tolerance_extension: Optional[float],
        critical_features: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Check if a value violates a range-based target."""
        min_val, max_val = target_range

        # Extend the range by tolerance on both sides
        if tolerance_extension is not None:
            extended_min = max(0, min_val - tolerance_extension)
            extended_max = min(
                1 if feature_name != "tempo" else 250, max_val + tolerance_extension
            )
        else:
            extended_min, extended_max = min_val, max_val

        # Check if value falls within extended range
        if actual_value < extended_min or actual_value > extended_max:
            distance_below = (
                extended_min - actual_value if actual_value < extended_min else 0
            )
            distance_above = (
                actual_value - extended_max if actual_value > extended_max else 0
            )
            distance = max(distance_below, distance_above)

            # Only flag as critical if it's a critical feature and significantly out of range
            is_critical = (
                feature_name in critical_features
                and tolerance_extension is not None
                and distance > tolerance_extension * 2
            )

            return {
                "description": (
                    f"{feature_name}: range=[{min_val:.2f}, {max_val:.2f}], "
                    f"extended=[{extended_min:.2f}, {extended_max:.2f}], "
                    f"actual={actual_value:.2f}, out_by={distance:.2f}"
                ),
                "is_critical": is_critical,
            }

        return None

    @classmethod
    def _check_single_value_violation(
        cls,
        feature_name: str,
        target_value: float,
        actual_value: float,
        tolerance_extension: Optional[float],
        critical_features: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Check if a value violates a single-value target."""
        if tolerance_extension is None:
            # Binary or discrete features - skip strict filtering
            if feature_name in ["mode", "key"]:
                return None
            return None

        # Check distance from target
        difference = abs(actual_value - target_value)
        if difference > tolerance_extension:
            # Only flag as critical if it's a critical feature and very far off
            is_critical = (
                feature_name in critical_features
                and difference > tolerance_extension * 2
            )

            return {
                "description": (
                    f"{feature_name}: target={target_value:.2f}, "
                    f"actual={actual_value:.2f}, diff={difference:.2f}"
                ),
                "is_critical": is_critical,
            }

        return None

    @classmethod
    def _get_tolerance_thresholds(cls, mode: str) -> Dict[str, float]:
        """Get tolerance thresholds based on mode.

        Args:
            mode: "base", "relaxed", or "extended"

        Returns:
            Dictionary of tolerance thresholds
        """
        if mode == "relaxed":
            return cls.RELAXED_TOLERANCE_THRESHOLDS
        elif mode == "extended":
            return cls.EXTENDED_TOLERANCE_THRESHOLDS
        else:
            return cls.BASE_TOLERANCE_THRESHOLDS
