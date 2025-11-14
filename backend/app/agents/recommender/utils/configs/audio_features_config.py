"""Audio feature configuration for mood matching."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AudioFeaturesConfig:
    """Configuration for audio feature weights, tolerances, and critical features."""

    # Feature weights for mood matching
    default_feature_weights: Dict[str, float] = field(default_factory=lambda: {
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
    })

    # Audio feature tolerance thresholds
    feature_tolerances: Dict[str, float] = field(default_factory=lambda: {
        "speechiness": 0.15,
        "instrumentalness": 0.15,
        "energy": 0.20,
        "valence": 0.25,
        "danceability": 0.20,
        "tempo": 30.0,
        "loudness": 5.0,
        "acousticness": 0.25,
        "liveness": 0.30,
        "popularity": 20
    })

    # Critical features that are most important for mood matching
    critical_features: List[str] = field(default_factory=lambda: [
        "energy", "acousticness", "instrumentalness", "danceability"
    ])
