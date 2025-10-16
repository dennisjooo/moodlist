"""Feature matcher for calculating mood match scores between tracks and target features."""

import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger(__name__)


class FeatureMatcher:
    """Handles feature matching and similarity calculations for seed selection."""

    def calculate_mood_match_score(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track matches target mood features using all available audio features and weights.

        Args:
            track: Track information from Spotify
            target_features: Target audio features from mood analysis (may include _weights)

        Returns:
            Match score (0-1, higher is better)
        """
        if not target_features:
            # Fallback to popularity if no target features
            return track.get("popularity", 50) / 100.0

        # Extract feature weights if provided, otherwise use defaults
        feature_weights = target_features.get("_weights", self._get_default_feature_weights())

        total_score = 0.0
        total_weight = 0.0

        # Calculate match score for each available feature
        for feature, target_value in target_features.items():
            if feature == "_weights" or feature not in feature_weights:
                continue

            weight = feature_weights.get(feature, 0.1)  # Default weight if not specified
            track_value = self._get_track_feature_value(track, feature)

            if track_value is not None:
                # Calculate similarity score (0-1) for this feature
                feature_score = self._calculate_feature_similarity(
                    track_value, target_value, feature
                )

                total_score += feature_score * weight
                total_weight += weight

        # Normalize by total weight
        if total_weight == 0:
            return track.get("popularity", 50) / 100.0

        final_score = total_score / total_weight

        # Boost score slightly for popular tracks (they're likely to be good seeds)
        popularity_boost = min(track.get("popularity", 50) / 1000.0, 0.1)

        return min(final_score + popularity_boost, 1.0)

    def _get_default_feature_weights(self) -> Dict[str, float]:
        """Get default feature weights when none are provided by mood analysis."""
        return {
            "energy": 0.15,
            "valence": 0.15,
            "danceability": 0.12,
            "acousticness": 0.12,
            "instrumentalness": 0.10,
            "tempo": 0.08,
            "mode": 0.08,
            "loudness": 0.06,
            "speechiness": 0.05,
            "liveness": 0.05,
            "key": 0.03,
            "popularity": 0.01
        }

    def _get_track_feature_value(self, track: Dict[str, Any], feature: str) -> Optional[float]:
        """Extract feature value from Spotify track data.

        Args:
            track: Spotify track information
            feature: Feature name to extract

        Returns:
            Feature value or None if not available
        """
        # Map feature names to Spotify track structure
        feature_mapping = {
            "energy": track.get("energy"),
            "valence": track.get("valence"),
            "danceability": track.get("danceability"),
            "acousticness": track.get("acousticness"),
            "instrumentalness": track.get("instrumentalness"),
            "tempo": track.get("tempo"),
            "mode": track.get("mode"),
            "loudness": track.get("loudness"),
            "speechiness": track.get("speechiness"),
            "liveness": track.get("liveness"),
            "key": track.get("key"),
            "popularity": track.get("popularity")
        }

        return feature_mapping.get(feature)

    def _calculate_feature_similarity(
        self,
        track_value: float,
        target_value: float,
        feature: str
    ) -> float:
        """Calculate similarity between track feature and target feature.

        Args:
            track_value: Actual feature value from track
            target_value: Target feature value from mood analysis
            feature: Name of the feature being compared

        Returns:
            Similarity score (0-1, higher is better)
        """
        if feature in ["tempo", "loudness", "key", "popularity"]:
            # For continuous numeric features, use distance-based similarity
            if feature == "tempo":
                # Tempo similarity - closer BPMs are more similar
                max_diff = 60  # BPM
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "loudness":
                # Loudness similarity - closer dB values are more similar
                max_diff = 30  # dB
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "key":
                # Key similarity - exact match or adjacent keys
                if track_value == target_value:
                    return 1.0
                elif abs(track_value - target_value) == 1:
                    return 0.8  # Adjacent keys are somewhat similar
                else:
                    return 0.3  # Other keys are less similar
            elif feature == "popularity":
                # Popularity similarity - lower popularity for indie moods
                max_diff = 100
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))

        # For normalized features (0-1), use direct distance
        diff = abs(track_value - target_value)
        return max(0, 1 - diff)