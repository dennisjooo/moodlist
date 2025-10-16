"""Text processing utilities for mood analysis."""

from typing import List

from ..utils import config


class TextProcessor:
    """Shared text processing utilities for mood analysis."""

    @staticmethod
    def extract_search_keywords(mood_prompt: str) -> List[str]:
        """Extract search keywords from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            List of relevant search keywords
        """
        # Simple keyword extraction - can be enhanced with NLP
        keywords = []

        # Split by common delimiters
        words = mood_prompt.replace(",", " ").replace(" and ", " ").split()

        # Filter meaningful words (length > 3, not common stop words)
        meaningful_words = [
            word.lower() for word in words
            if len(word) > 3 and word.lower() not in config.stop_words
        ]

        keywords.extend(meaningful_words)

        # Add some common mood-related terms
        for word in meaningful_words:
            if word in config.mood_synonyms:
                keywords.extend(config.mood_synonyms[word])

        return list(set(keywords))  # Remove duplicates

    @staticmethod
    def extract_genres_and_artists(mood_prompt: str) -> tuple[List[str], List[str]]:
        """Extract genre keywords and artist names from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            Tuple of (genre_keywords, artist_recommendations)
        """
        prompt_lower = mood_prompt.lower()
        genre_keywords = []
        artist_recommendations = []

        # Check for known genres
        for genre in config.known_genres:
            if genre in prompt_lower:
                # Normalize genre (remove spaces for search)
                normalized_genre = genre.replace(" ", "").replace("-", "")
                genre_keywords.append(normalized_genre)

        # Simple heuristic: Look for capitalized words that might be artist names
        # This is a basic approach - could be enhanced with NLP/entity recognition
        words = mood_prompt.split()
        for i, word in enumerate(words):
            # Check if word is capitalized (and not at start of sentence)
            if word and word[0].isupper() and i > 0:
                # Check if it's part of a multi-word name
                potential_artist = word
                # Look ahead for more capitalized words
                j = i + 1
                while j < len(words) and words[j] and words[j][0].isupper():
                    potential_artist += " " + words[j]
                    j += 1

                # Only add if not a genre keyword
                if potential_artist.lower() not in config.known_genres:
                    artist_recommendations.append(potential_artist)

        # Remove duplicates
        genre_keywords = list(set(genre_keywords))
        artist_recommendations = list(set(artist_recommendations))

        return genre_keywords, artist_recommendations

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect the language of a text based on common indicators.

        Args:
            text: Text to analyze

        Returns:
            Detected language ('english', 'spanish', 'french', etc.) or 'unknown'
        """
        text_lower = text.lower()

        # Check for language-specific keywords or patterns
        for lang, indicators in config.language_indicators.items():
            for indicator in indicators:
                if isinstance(indicator, str):
                    if indicator in text_lower:
                        return lang
                else:
                    # Unicode range check for CJK languages
                    for char in text:
                        if indicator <= char <= config.language_indicators[lang][config.language_indicators[lang].index(indicator) + 1]:
                            return lang

        return "english"  # Default fallback
