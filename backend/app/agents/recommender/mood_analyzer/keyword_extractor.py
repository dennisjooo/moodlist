"""Keyword extractor for parsing mood prompts and extracting keywords."""

from typing import List


class KeywordExtractor:
    """Extracts keywords and metadata from mood prompts."""

    def __init__(self):
        """Initialize the keyword extractor."""
        pass

    def extract_search_keywords(self, mood_prompt: str) -> List[str]:
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
        stop_words = {"for", "with", "that", "this", "very", "some", "music", "songs", "playlist"}
        meaningful_words = [
            word.lower() for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]

        keywords.extend(meaningful_words)

        # Add some common mood-related terms
        mood_synonyms = {
            "chill": ["relaxed", "laid-back", "mellow"],
            "energetic": ["upbeat", "lively", "dynamic"],
            "sad": ["melancholy", "emotional", "bittersweet"],
            "happy": ["joyful", "cheerful", "uplifting"],
            "romantic": ["love", "intimate", "passionate"],
            "focus": ["concentration", "study", "instrumental"],
            "party": ["celebration", "fun", "dance"],
            "workout": ["fitness", "motivation", "pump"],
        }

        for word in meaningful_words:
            if word in mood_synonyms:
                keywords.extend(mood_synonyms[word])

        return list(set(keywords))  # Remove duplicates

    def extract_genres_and_artists(self, mood_prompt: str) -> tuple[List[str], List[str]]:
        """Extract genre keywords and artist names from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            Tuple of (genre_keywords, artist_recommendations)
        """
        # Common genre keywords that should be searched as genres
        known_genres = {
            "indie", "rock", "pop", "jazz", "electronic", "edm", "hip-hop", "hip hop",
            "rap", "r&b", "rnb", "soul", "funk", "disco", "house", "techno", "trance",
            "dubstep", "drum and bass", "dnb", "ambient", "classical", "country", "folk",
            "metal", "punk", "alternative", "grunge", "ska", "reggae", "blues", "gospel",
            "latin", "salsa", "bossa nova", "samba", "k-pop", "kpop", "j-pop", "jpop",
            "city pop", "citypop", "synthwave", "vaporwave", "lo-fi", "lofi", "chillwave",
            "shoegaze", "post-rock", "post-punk", "new wave", "psychedelic", "progressive"
        }

        prompt_lower = mood_prompt.lower()
        genre_keywords = []
        artist_recommendations = []

        # Check for known genres
        for genre in known_genres:
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
                if potential_artist.lower() not in known_genres:
                    artist_recommendations.append(potential_artist)

        # Remove duplicates
        genre_keywords = list(set(genre_keywords))
        artist_recommendations = list(set(artist_recommendations))

        return genre_keywords, artist_recommendations