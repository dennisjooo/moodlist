"""Text processing configuration for the recommender system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class TextProcessingConfig:
    """Configuration for text processing, stop words, genres, and language detection."""

    # Text processing constants
    stop_words: Set[str] = field(default_factory=lambda: {
        "for", "with", "that", "this", "very", "some", "music", "songs", "playlist"
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
