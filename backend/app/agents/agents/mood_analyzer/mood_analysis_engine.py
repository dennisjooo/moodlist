"""Mood analysis engine for LLM-based and fallback mood analysis."""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from .prompts import get_mood_analysis_system_prompt

logger = logging.getLogger(__name__)


class MoodAnalysisEngine:
    """Engine for analyzing mood prompts using LLM or fallback methods."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """Initialize the mood analysis engine.

        Args:
            llm: Language model for mood analysis
        """
        self.llm = llm

    async def analyze_mood(self, mood_prompt: str) -> Dict[str, Any]:
        """Analyze mood using LLM or fallback method.

        Args:
            mood_prompt: User's mood description

        Returns:
            Comprehensive mood analysis
        """
        if self.llm:
            return await self._analyze_mood_with_llm(mood_prompt)
        else:
            return self._analyze_mood_fallback(mood_prompt)

    async def _analyze_mood_with_llm(self, mood_prompt: str) -> Dict[str, Any]:
        """Analyze mood using LLM.

        Args:
            mood_prompt: User's mood description

        Returns:
            Comprehensive mood analysis
        """
        try:
            # Create prompt
            messages = [
                {"role": "system", "content": get_mood_analysis_system_prompt()},
                {"role": "user", "content": f"Analyze this mood: '{mood_prompt}'"}
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Try to parse JSON response
            try:
                # Extract JSON from response
                content = response.content if hasattr(response, 'content') else str(response)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # Fallback if no JSON found
                    analysis = self._parse_llm_response_fallback(content)

            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.error(f"JSON parsing failed: {response}")
                analysis = self._parse_llm_response_fallback(response)

            return analysis

        except Exception as e:
            logger.error(f"LLM mood analysis failed: {str(e)}")
            return self._analyze_mood_fallback(mood_prompt)

    def _analyze_mood_fallback(self, mood_prompt: str) -> Dict[str, Any]:
        """Enhanced fallback rule-based mood analysis with full feature set.

        Args:
            mood_prompt: User's mood description

        Returns:
            Comprehensive mood analysis with all 12 audio features
        """
        prompt_lower = mood_prompt.lower()

        # Enhanced analysis structure
        analysis = {
            "mood_interpretation": f"Rule-based analysis of: {mood_prompt}",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "feature_weights": {},
            "search_keywords": [],
            "artist_recommendations": [],
            "genre_keywords": [],
            "reasoning": f"Rule-based analysis using keyword matching for: {mood_prompt}"
        }

        # Define mood profiles for common scenarios
        mood_profiles = {
            "indie": {
                "keywords": ["indie", "alternative", "underground", "independent"],
                "features": {
                    "acousticness": [0.6, 1.0],
                    "energy": [0.2, 0.6],
                    "popularity": [0, 40],
                    "loudness": [-20, -5],
                    "instrumentalness": [0.2, 0.8]
                },
                "weights": {"acousticness": 0.9, "popularity": 0.8, "energy": 0.7}
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
                "weights": {"energy": 0.9, "danceability": 0.9, "valence": 0.8}
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
                "weights": {"energy": 0.9, "acousticness": 0.8, "tempo": 0.7}
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
                "weights": {"instrumentalness": 0.9, "speechiness": 0.8, "energy": 0.7}
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
                "weights": {"valence": 0.9, "mode": 0.8, "acousticness": 0.7}
            }
        }

        # Check for mood profile matches
        matched_profiles = []
        for mood_name, profile in mood_profiles.items():
            if any(keyword in prompt_lower for keyword in profile["keywords"]):
                matched_profiles.append((mood_name, profile))

        # Apply matched profiles
        if matched_profiles:
            for mood_name, profile in matched_profiles:
                analysis["mood_interpretation"] = f"{mood_name.capitalize()} mood based on: {mood_prompt}"
                analysis["target_features"].update(profile["features"])
                analysis["feature_weights"].update(profile["weights"])

                # Update primary emotion based on mood
                emotion_mapping = {
                    "party": "positive",
                    "chill": "neutral",
                    "focus": "neutral",
                    "emotional": "negative",
                    "indie": "neutral"
                }
                if mood_name in emotion_mapping:
                    analysis["primary_emotion"] = emotion_mapping[mood_name]

        # Additional keyword-based feature analysis
        self._enhance_features_with_keywords(analysis, prompt_lower)

        # Generate search keywords
        analysis["search_keywords"] = self._extract_search_keywords(mood_prompt)

        # Extract genre keywords and artist recommendations
        genre_keywords, artist_recommendations = self._extract_genres_and_artists(mood_prompt)
        analysis["genre_keywords"] = genre_keywords
        analysis["artist_recommendations"] = artist_recommendations

        return analysis

    def _enhance_features_with_keywords(self, analysis: Dict[str, Any], prompt_lower: str):
        """Enhance feature analysis with specific keywords."""
        # Energy analysis
        high_energy_keywords = ["energetic", "upbeat", "exciting", "workout", "intense", "powerful", "hype"]
        low_energy_keywords = ["calm", "peaceful", "sleepy", "soft", "gentle", "laid-back"]

        if any(keyword in prompt_lower for keyword in high_energy_keywords):
            analysis["energy_level"] = "high"
            if "energy" not in analysis["target_features"]:
                analysis["target_features"]["energy"] = [0.7, 1.0]
                analysis["target_features"]["valence"] = [0.5, 1.0]
        elif any(keyword in prompt_lower for keyword in low_energy_keywords):
            analysis["energy_level"] = "low"
            if "energy" not in analysis["target_features"]:
                analysis["target_features"]["energy"] = [0.0, 0.4]

        # Valence analysis
        positive_keywords = ["happy", "joyful", "cheerful", "uplifting", "fun", "bright"]
        negative_keywords = ["sad", "depressed", "dark", "moody", "bittersweet"]

        if any(keyword in prompt_lower for keyword in positive_keywords):
            analysis["primary_emotion"] = "positive"
            if "valence" not in analysis["target_features"]:
                analysis["target_features"]["valence"] = [0.7, 1.0]
        elif any(keyword in prompt_lower for keyword in negative_keywords):
            analysis["primary_emotion"] = "negative"
            if "valence" not in analysis["target_features"]:
                analysis["target_features"]["valence"] = [0.0, 0.4]

        # Danceability analysis
        dance_keywords = ["dance", "dancing", "groove", "rhythm", "club"]
        if any(keyword in prompt_lower for keyword in dance_keywords):
            if "danceability" not in analysis["target_features"]:
                analysis["target_features"]["danceability"] = [0.6, 1.0]

        # Acousticness analysis
        acoustic_keywords = ["acoustic", "unplugged", "organic", "folk", "singer-songwriter"]
        if any(keyword in prompt_lower for keyword in acoustic_keywords):
            if "acousticness" not in analysis["target_features"]:
                analysis["target_features"]["acousticness"] = [0.7, 1.0]

        # Instrumentalness analysis
        instrumental_keywords = ["instrumental", "no vocals", "background", "ambient"]
        if any(keyword in prompt_lower for keyword in instrumental_keywords):
            if "instrumentalness" not in analysis["target_features"]:
                analysis["target_features"]["instrumentalness"] = [0.7, 1.0]

        # Live performance analysis
        live_keywords = ["live", "concert", "performance", "audience"]
        if any(keyword in prompt_lower for keyword in live_keywords):
            if "liveness" not in analysis["target_features"]:
                analysis["target_features"]["liveness"] = [0.6, 1.0]

        # Speech/Talk analysis
        speech_keywords = ["podcast", "talk", "spoken", "narrative", "story"]
        if any(keyword in prompt_lower for keyword in speech_keywords):
            if "speechiness" not in analysis["target_features"]:
                analysis["target_features"]["speechiness"] = [0.5, 1.0]

    def _parse_llm_response_fallback(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response when JSON parsing fails.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed mood analysis
        """
        content_lower = response_content.lower()

        analysis = {
            "mood_interpretation": response_content[:200] + "...",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "search_keywords": [],
            "reasoning": response_content
        }

        # Extract basic features from text
        if "high energy" in content_lower or "energetic" in content_lower:
            analysis["energy_level"] = "high"
            analysis["target_features"]["energy"] = [0.7, 1.0]

        if "low energy" in content_lower or "calm" in content_lower:
            analysis["energy_level"] = "low"
            analysis["target_features"]["energy"] = [0.0, 0.4]

        if "happy" in content_lower or "positive" in content_lower:
            analysis["primary_emotion"] = "positive"
            analysis["target_features"]["valence"] = [0.7, 1.0]

        if "sad" in content_lower or "negative" in content_lower:
            analysis["primary_emotion"] = "negative"
            analysis["target_features"]["valence"] = [0.0, 0.4]

        return analysis

    def _extract_search_keywords(self, mood_prompt: str) -> List[str]:
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

    def _extract_genres_and_artists(self, mood_prompt: str) -> tuple[List[str], List[str]]:
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