"""Keyword extractor for parsing mood prompts and extracting keywords."""

from typing import List

from .text_processor import TextProcessor


class KeywordExtractor:
    """Extracts keywords and metadata from mood prompts using shared text processing utilities."""

    def __init__(self):
        """Initialize the keyword extractor."""
        self._processor = TextProcessor()

    def extract_search_keywords(self, mood_prompt: str) -> List[str]:
        """Extract search keywords from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            List of relevant search keywords
        """
        return self._processor.extract_search_keywords(mood_prompt)

    def extract_genres_and_artists(
        self, mood_prompt: str
    ) -> tuple[List[str], List[str]]:
        """Extract genre keywords and artist names from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            Tuple of (genre_keywords, artist_recommendations)
        """
        return self._processor.extract_genres_and_artists(mood_prompt)
