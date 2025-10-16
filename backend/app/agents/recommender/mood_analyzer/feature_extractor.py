"""Feature extractor for audio feature extraction and weighting."""

import structlog
from typing import Any, Dict

logger = structlog.get_logger(__name__)


class FeatureExtractor:
    """Extracts and processes audio features from mood analysis."""

    def __init__(self):
        """Initialize the feature extractor."""
        pass

    def extract_target_features(self, mood_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract target audio features from mood analysis with full feature set support.

        Args:
            mood_analysis: Comprehensive mood analysis

        Returns:
            Dictionary of target audio features (midpoint of ranges)
        """
        target_features = {}

        features = mood_analysis.get("target_features", {})

        # Convert ranges to target values (use midpoint)
        for feature, value_range in features.items():
            if isinstance(value_range, list) and len(value_range) == 2:
                # Use midpoint of range as target value
                target_features[feature] = sum(value_range) / 2
            elif isinstance(value_range, (int, float)):
                target_features[feature] = float(value_range)

        # Ensure we have reasonable defaults for key features if missing
        if not target_features:
            logger.warning("No target features extracted from mood analysis")
            # Set neutral defaults
            target_features = {
                "energy": 0.5,
                "valence": 0.5,
                "danceability": 0.5,
                "acousticness": 0.5
            }

        logger.info(f"Extracted target features: {list(target_features.keys())}")
        return target_features

    def extract_feature_weights(self, mood_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract feature importance weights from mood analysis.

        Args:
            mood_analysis: Comprehensive mood analysis

        Returns:
            Dictionary of feature weights (0-1 importance)
        """
        feature_weights = mood_analysis.get("feature_weights", {})

        # Set default weights if none provided
        if not feature_weights:
            # Default weights favoring core mood features
            feature_weights = {
                "energy": 0.8,
                "valence": 0.8,
                "danceability": 0.6,
                "acousticness": 0.6,
                "instrumentalness": 0.5,
                "tempo": 0.4,
                "mode": 0.4,
                "loudness": 0.3,
                "speechiness": 0.3,
                "liveness": 0.2,
                "key": 0.2,
                "popularity": 0.1
            }

        return feature_weights