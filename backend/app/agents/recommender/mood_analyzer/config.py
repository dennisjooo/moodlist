"""Configuration constants for mood analysis."""

from typing import Any, Dict, List, Set

# Text processing constants
STOP_WORDS: Set[str] = {
    "for",
    "with",
    "that",
    "this",
    "very",
    "some",
    "music",
    "songs",
    "playlist",
}

MOOD_SYNONYMS: Dict[str, List[str]] = {
    "chill": ["relaxed", "laid-back", "mellow"],
    "energetic": ["upbeat", "lively", "dynamic"],
    "sad": ["melancholy", "emotional", "bittersweet"],
    "happy": ["joyful", "cheerful", "uplifting"],
    "romantic": ["love", "intimate", "passionate"],
    "focus": ["concentration", "study", "instrumental"],
    "party": ["celebration", "fun", "dance"],
    "workout": ["fitness", "motivation", "pump"],
}

# Known genre keywords that should be searched as genres
KNOWN_GENRES: Set[str] = {
    "indie",
    "rock",
    "pop",
    "jazz",
    "electronic",
    "edm",
    "hip-hop",
    "hip hop",
    "rap",
    "r&b",
    "rnb",
    "soul",
    "funk",
    "disco",
    "house",
    "techno",
    "trance",
    "dubstep",
    "drum and bass",
    "dnb",
    "ambient",
    "classical",
    "country",
    "folk",
    "metal",
    "punk",
    "alternative",
    "grunge",
    "ska",
    "reggae",
    "blues",
    "gospel",
    "latin",
    "salsa",
    "bossa nova",
    "samba",
    "k-pop",
    "kpop",
    "j-pop",
    "jpop",
    "city pop",
    "citypop",
    "synthwave",
    "vaporwave",
    "lo-fi",
    "lofi",
    "chillwave",
    "shoegaze",
    "post-rock",
    "post-punk",
    "new wave",
    "psychedelic",
    "progressive",
}

# Language detection indicators
LANGUAGE_INDICATORS: Dict[str, List[str]] = {
    "spanish": [
        "el ",
        "la ",
        "los ",
        "las ",
        "mi ",
        "tu ",
        "de ",
        "con ",
        "por ",
        "para ",
    ],
    "korean": ["\u3131", "\u314f", "\uac00", "\ud7a3"],  # Hangul character ranges
    "japanese": ["\u3040", "\u309f", "\u30a0", "\u30ff"],  # Hiragana/Katakana
    "chinese": ["\u4e00", "\u9fff"],  # Common CJK
    "portuguese": ["meu ", "minha ", "você ", "está ", "muito ", "bem "],
    "german": ["der ", "die ", "das ", "ich ", "du ", "und ", "mit "],
    "french": ["le ", "la ", "les ", "de ", "je ", "tu ", "avec ", "pour "],
}

# Mood profiles for rule-based mood analysis
MOOD_PROFILES: Dict[str, Dict[str, Any]] = {
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
        "keywords": ["focus", "concentration", "study", "instrumental", "ambient"],
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
