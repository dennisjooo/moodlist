"""Centralized configuration for the recommender package."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class RecommenderConfig:
    """Centralized configuration for the recommender system."""

    # Orchestration settings
    max_iterations: int = 2  # Reduced from 3 for faster generation
    cohesion_threshold: float = 0.60  # Relaxed from 0.65 for speed while maintaining quality
    quality_threshold: float = 0.75

    # Recommendation generation settings
    max_recommendations: int = 30
    diversity_factor: float = 0.7
    artist_recommendation_ratio: float = 0.95  # 95% artist, 5% RecoBeat
    min_playlist_count: int = 15
    max_playlist_count: int = 30

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

    # Text processing constants
    stop_words: Set[str] = field(default_factory=lambda: {
        "for", "with", "that", "this", "very", "some", "music", "songs", "playlist"
    })

    # Mood synonym mappings
    mood_synonyms: Dict[str, List[str]] = field(default_factory=lambda: {
        "chill": ["relaxed", "laid-back", "mellow"],
        "energetic": ["upbeat", "lively", "dynamic"],
        "sad": ["melancholy", "emotional", "bittersweet"],
        "happy": ["joyful", "cheerful", "uplifting"],
        "romantic": ["love", "intimate", "passionate"],
        "focus": ["concentration", "study", "instrumental"],
        "party": ["celebration", "fun", "dance"],
        "workout": ["fitness", "motivation", "pump"],
    })

    # Known genre keywords for search
    known_genres: Set[str] = field(default_factory=lambda: {
        "indie", "rock", "pop", "jazz", "electronic", "edm", "hip-hop", "hip hop",
        "rap", "r&b", "rnb", "soul", "funk", "disco", "house", "techno", "trance",
        "dubstep", "drum and bass", "dnb", "ambient", "classical", "country", "folk",
        "metal", "punk", "alternative", "grunge", "ska", "reggae", "blues", "gospel",
        "latin", "salsa", "bossa nova", "samba", "k-pop", "kpop", "j-pop", "jpop",
        "city pop", "citypop", "synthwave", "vaporwave", "lo-fi", "lofi", "chillwave",
        "shoegaze", "post-rock", "post-punk", "new wave", "psychedelic", "progressive"
    })

    # Language detection indicators
    language_indicators: Dict[str, List[Any]] = field(default_factory=lambda: {
        "spanish": ["el ", "la ", "los ", "las ", "mi ", "tu ", "de ", "con ", "por ", "para "],
        "korean": ["\u3131", "\u314f", "\uac00", "\ud7a3"],  # Hangul character ranges
        "japanese": ["\u3040", "\u309f", "\u30a0", "\u30ff"],  # Hiragana/Katakana
        "chinese": ["\u4e00", "\u9fff"],  # Common CJK
        "portuguese": ["meu ", "minha ", "você ", "está ", "muito ", "bem "],
        "german": ["der ", "die ", "das ", "ich ", "du ", "und ", "mit "],
        "french": ["le ", "la ", "les ", "de ", "je ", "tu ", "avec ", "pour "]
    })

    # Mood profiles for rule-based mood analysis
    mood_profiles: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "indie": {
            "keywords": ["indie", "alternative", "underground", "independent"],
            "features": {
                "acousticness": [0.6, 1.0],
                "energy": [0.2, 0.6],
                "popularity": [0, 40],
                "loudness": [-20, -5],
                "instrumentalness": [0.2, 0.8]
            },
            "weights": {"acousticness": 0.9, "popularity": 0.8, "energy": 0.7},
            "emotion": "neutral"
        },
        "party": {
            "keywords": ["party", "celebration", "dance", "club", "energetic"],
            "features": {
                "energy": [0.7, 1.0],
                "danceability": [0.7, 1.0],
                "valence": [0.6, 1.0],
                "tempo": [110, 140],
                "loudness": [-10, -2]
            },
            "weights": {"energy": 0.9, "danceability": 0.9, "valence": 0.8},
            "emotion": "positive"
        },
        "chill": {
            "keywords": ["chill", "relaxed", "calm", "peaceful", "mellow"],
            "features": {
                "energy": [0.0, 0.4],
                "acousticness": [0.5, 1.0],
                "valence": [0.4, 0.8],
                "tempo": [60, 100],
                "loudness": [-25, -10]
            },
            "weights": {"energy": 0.9, "acousticness": 0.8, "tempo": 0.7},
            "emotion": "neutral"
        },
        "focus": {
            "keywords": ["focus", "concentration", "study", "instrumental", "ambient"],
            "features": {
                "instrumentalness": [0.7, 1.0],
                "energy": [0.1, 0.4],
                "acousticness": [0.4, 1.0],
                "speechiness": [0.0, 0.2],
                "tempo": [50, 90]
            },
            "weights": {"instrumentalness": 0.9, "speechiness": 0.8, "energy": 0.7},
            "emotion": "neutral"
        },
        "emotional": {
            "keywords": ["emotional", "sad", "melancholy", "deep", "sentimental"],
            "features": {
                "valence": [0.0, 0.4],
                "energy": [0.1, 0.5],
                "mode": [0, 0.3],  # Minor key preference
                "acousticness": [0.4, 1.0],
                "tempo": [60, 110]
            },
            "weights": {"valence": 0.9, "mode": 0.8, "acousticness": 0.7},
            "emotion": "negative"
        }
    })

    # Keyword-to-feature mappings for mood analysis
    keyword_feature_mappings: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "keywords": ["energetic", "upbeat", "exciting", "workout", "intense", "powerful", "hype"],
            "emotion_level": ("energy_level", "high"),
            "features": {
                "energy": [0.7, 1.0],
                "valence": [0.5, 1.0]
            }
        },
        {
            "keywords": ["calm", "peaceful", "sleepy", "soft", "gentle", "laid-back"],
            "emotion_level": ("energy_level", "low"),
            "features": {"energy": [0.0, 0.4]}
        },
        {
            "keywords": ["happy", "joyful", "cheerful", "uplifting", "fun", "bright"],
            "emotion_level": ("primary_emotion", "positive"),
            "features": {"valence": [0.7, 1.0]}
        },
        {
            "keywords": ["sad", "depressed", "dark", "moody", "bittersweet"],
            "emotion_level": ("primary_emotion", "negative"),
            "features": {"valence": [0.0, 0.4]}
        },
        {
            "keywords": ["dance", "dancing", "groove", "rhythm", "club"],
            "features": {"danceability": [0.6, 1.0]}
        },
        {
            "keywords": ["acoustic", "unplugged", "organic", "folk", "singer-songwriter"],
            "features": {"acousticness": [0.7, 1.0]}
        },
        {
            "keywords": ["instrumental", "no vocals", "background", "ambient"],
            "features": {"instrumentalness": [0.7, 1.0]}
        },
        {
            "keywords": ["live", "concert", "performance", "audience"],
            "features": {"liveness": [0.6, 1.0]}
        },
        {
            "keywords": ["podcast", "talk", "spoken", "narrative", "story"],
            "features": {"speechiness": [0.5, 1.0]}
        }
    ])


# Global configuration instance
config = RecommenderConfig()
