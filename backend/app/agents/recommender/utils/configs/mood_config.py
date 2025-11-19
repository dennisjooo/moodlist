"""Mood-related configuration for the recommender system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MoodConfig:
    """Configuration for mood profiles, synonyms, and keyword mappings."""

    # Mood synonym mappings
    mood_synonyms: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "chill": ["relaxed", "laid-back", "mellow"],
            "energetic": ["upbeat", "lively", "dynamic"],
            "sad": ["melancholy", "emotional", "bittersweet"],
            "happy": ["joyful", "cheerful", "uplifting"],
            "romantic": ["love", "intimate", "passionate"],
            "focus": ["concentration", "study", "instrumental"],
            "party": ["celebration", "fun", "dance"],
            "workout": ["fitness", "motivation", "pump"],
        }
    )

    # Mood profiles for rule-based mood analysis
    mood_profiles: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "indie": {
                "keywords": ["indie", "alternative", "underground", "independent"],
                "features": {
                    "acousticness": [0.6, 1.0],
                    "energy": [0.2, 0.6],
                    "popularity": [0, 40],
                    "loudness": [-20, -5],
                    "instrumentalness": [0.2, 0.8],
                },
                "weights": {"acousticness": 0.9, "popularity": 0.8, "energy": 0.7},
                "emotion": "neutral",
            },
            "party": {
                "keywords": ["party", "celebration", "dance", "club", "energetic"],
                "features": {
                    "energy": [0.7, 1.0],
                    "danceability": [0.7, 1.0],
                    "valence": [0.6, 1.0],
                    "tempo": [110, 140],
                    "loudness": [-10, -2],
                },
                "weights": {"energy": 0.9, "danceability": 0.9, "valence": 0.8},
                "emotion": "positive",
            },
            "chill": {
                "keywords": ["chill", "relaxed", "calm", "peaceful", "mellow"],
                "features": {
                    "energy": [0.0, 0.4],
                    "acousticness": [0.5, 1.0],
                    "valence": [0.4, 0.8],
                    "tempo": [60, 100],
                    "loudness": [-25, -10],
                },
                "weights": {"energy": 0.9, "acousticness": 0.8, "tempo": 0.7},
                "emotion": "neutral",
            },
            "focus": {
                "keywords": [
                    "focus",
                    "concentration",
                    "study",
                    "instrumental",
                    "ambient",
                ],
                "features": {
                    "instrumentalness": [0.7, 1.0],
                    "energy": [0.1, 0.4],
                    "acousticness": [0.4, 1.0],
                    "speechiness": [0.0, 0.2],
                    "tempo": [50, 90],
                },
                "weights": {"instrumentalness": 0.9, "speechiness": 0.8, "energy": 0.7},
                "emotion": "neutral",
            },
            "emotional": {
                "keywords": ["emotional", "sad", "melancholy", "deep", "sentimental"],
                "features": {
                    "valence": [0.0, 0.4],
                    "energy": [0.1, 0.5],
                    "mode": [0, 0.3],  # Minor key preference
                    "acousticness": [0.4, 1.0],
                    "tempo": [60, 110],
                },
                "weights": {"valence": 0.9, "mode": 0.8, "acousticness": 0.7},
                "emotion": "negative",
            },
        }
    )

    # Keyword-to-feature mappings for mood analysis
    keyword_feature_mappings: List[Dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "keywords": [
                    "energetic",
                    "upbeat",
                    "exciting",
                    "workout",
                    "intense",
                    "powerful",
                    "hype",
                ],
                "emotion_level": ("energy_level", "high"),
                "features": {"energy": [0.7, 1.0], "valence": [0.5, 1.0]},
            },
            {
                "keywords": [
                    "calm",
                    "peaceful",
                    "sleepy",
                    "soft",
                    "gentle",
                    "laid-back",
                ],
                "emotion_level": ("energy_level", "low"),
                "features": {"energy": [0.0, 0.4]},
            },
            {
                "keywords": [
                    "happy",
                    "joyful",
                    "cheerful",
                    "uplifting",
                    "fun",
                    "bright",
                ],
                "emotion_level": ("primary_emotion", "positive"),
                "features": {"valence": [0.7, 1.0]},
            },
            {
                "keywords": ["sad", "depressed", "dark", "moody", "bittersweet"],
                "emotion_level": ("primary_emotion", "negative"),
                "features": {"valence": [0.0, 0.4]},
            },
            {
                "keywords": ["dance", "dancing", "groove", "rhythm", "club"],
                "features": {"danceability": [0.6, 1.0]},
            },
            {
                "keywords": [
                    "acoustic",
                    "unplugged",
                    "organic",
                    "folk",
                    "singer-songwriter",
                ],
                "features": {"acousticness": [0.7, 1.0]},
            },
            {
                "keywords": ["instrumental", "no vocals", "background", "ambient"],
                "features": {"instrumentalness": [0.7, 1.0]},
            },
            {
                "keywords": ["live", "concert", "performance", "audience"],
                "features": {"liveness": [0.6, 1.0]},
            },
            {
                "keywords": ["podcast", "talk", "spoken", "narrative", "story"],
                "features": {"speechiness": [0.5, 1.0]},
            },
        ]
    )
