"""Mood analysis engine for LLM-based and fallback mood analysis."""

from typing import Any, Dict, List, Optional, Union

import structlog
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import AIMessage

from ...utils.llm_response_parser import LLMResponseParser
from ..prompts import get_mood_analysis_system_prompt
from ..text import TextProcessor
from .mood_profile_matcher import MoodProfileMatcher

logger = structlog.get_logger(__name__)


class MoodAnalysisEngine:
    """Engine for analyzing mood prompts using LLM or fallback methods."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """Initialize the mood analysis engine.

        Args:
            llm: Language model for mood analysis
        """
        self.llm = llm
        self._text_processor = TextProcessor()
        self._profile_matcher = MoodProfileMatcher()

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
                {"role": "user", "content": f"Analyze this mood: '{mood_prompt}'"},
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Parse JSON response using centralized parser
            analysis = LLMResponseParser.extract_json_from_response(response)

            if not analysis:
                # Fallback if parsing fails
                logger.warning("Failed to parse JSON from LLM response, using fallback")
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
            "reasoning": f"Rule-based analysis using keyword matching for: {mood_prompt}",
        }

        # Match and apply mood profiles
        matched_profiles = self._profile_matcher.match_mood_profiles(mood_prompt)
        self._profile_matcher.apply_mood_profiles(
            matched_profiles, mood_prompt, analysis
        )

        # Additional keyword-based feature analysis
        self._enhance_features_with_keywords(analysis, prompt_lower)

        # Generate search keywords
        analysis["search_keywords"] = self._text_processor.extract_search_keywords(
            mood_prompt
        )

        # Extract genre keywords and artist recommendations
        genre_keywords, artist_recommendations = (
            self._text_processor.extract_genres_and_artists(mood_prompt)
        )
        analysis["genre_keywords"] = genre_keywords
        analysis["artist_recommendations"] = artist_recommendations

        # Add regional context (rule-based inference)
        preferred_regions, excluded_regions = self._infer_regional_context(prompt_lower)
        analysis["preferred_regions"] = preferred_regions
        analysis["excluded_regions"] = excluded_regions

        # Add theme exclusions (rule-based inference)
        excluded_themes = self._infer_excluded_themes(prompt_lower)
        analysis["excluded_themes"] = excluded_themes

        return analysis

    def _infer_regional_context(self, prompt_lower: str) -> tuple[List[str], List[str]]:
        """Infer regional preferences from the mood prompt.

        Args:
            prompt_lower: Lowercase mood prompt

        Returns:
            Tuple of (preferred_regions, excluded_regions)
        """
        preferred = []
        excluded = []

        # French/European indicators
        if any(term in prompt_lower for term in ["french", "france", "parisian"]):
            preferred.extend(["French", "European", "Western"])
            excluded.extend(["Southeast Asian", "Indonesian", "Eastern European"])

        # General European
        elif any(
            term in prompt_lower
            for term in ["european", "euro", "nu-disco", "house", "disco"]
        ):
            preferred.extend(["European", "Western"])
            excluded.extend(["Southeast Asian", "Indonesian"])

        # K-pop / Asian
        elif any(
            term in prompt_lower
            for term in [
                "k-pop",
                "kpop",
                "korean",
                "j-pop",
                "jpop",
                "japanese",
                "anime",
            ]
        ):
            preferred.append("Asian")
            excluded.extend(["Southeast Asian", "Western"])

        # Latin
        elif any(
            term in prompt_lower
            for term in ["latin", "reggaeton", "spanish", "salsa", "bachata"]
        ):
            preferred.append("Latin American")
            excluded.extend(["Southeast Asian", "Asian"])

        # Default to Western if no specific region detected
        elif not preferred:
            preferred.append("Western")
            excluded.extend(["Southeast Asian", "Indonesian"])

        return preferred, excluded

    def _infer_excluded_themes(self, prompt_lower: str) -> List[str]:
        """Infer themes that should be excluded from the mood prompt.

        Args:
            prompt_lower: Lowercase mood prompt

        Returns:
            List of excluded themes
        """
        excluded = []

        # Check if specific themes are explicitly requested (then don't exclude them)
        if any(
            term in prompt_lower for term in ["christmas", "holiday", "xmas", "festive"]
        ):
            # User wants holiday music, don't exclude it
            return []

        if any(
            term in prompt_lower for term in ["gospel", "worship", "praise", "church"]
        ):
            # User wants religious music, don't exclude it
            return []

        if any(term in prompt_lower for term in ["kids", "children", "nursery"]):
            # User wants kids music, don't exclude it
            return []

        # Default exclusions for most playlists (unless explicitly requested above)
        # Most people don't want holiday songs in their regular playlists
        excluded.extend(["holiday", "christmas"])

        # For specific genres/moods, add more exclusions
        if any(
            term in prompt_lower
            for term in ["romantic", "date", "dinner", "intimate", "sensual"]
        ):
            # Romantic moods should exclude religious themes
            excluded.extend(["religious", "kids"])

        if any(
            term in prompt_lower for term in ["workout", "gym", "exercise", "running"]
        ):
            # Workout playlists should exclude slow/ballad themes
            excluded.extend(["religious", "kids"])

        if any(term in prompt_lower for term in ["party", "dance", "club", "hype"]):
            # Party moods should exclude solemn themes
            excluded.extend(["religious", "kids"])

        if any(
            term in prompt_lower
            for term in ["chill", "relax", "study", "focus", "ambient"]
        ):
            # Chill/focus moods should exclude comedy and kids
            excluded.extend(["comedy", "kids"])

        # Remove duplicates
        return list(set(excluded))

    def _enhance_features_with_keywords(
        self, analysis: Dict[str, Any], prompt_lower: str
    ):
        """Enhance feature analysis with specific keywords."""
        # Energy analysis
        high_energy_keywords = [
            "energetic",
            "upbeat",
            "exciting",
            "workout",
            "intense",
            "powerful",
            "hype",
        ]
        low_energy_keywords = [
            "calm",
            "peaceful",
            "sleepy",
            "soft",
            "gentle",
            "laid-back",
        ]

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
        positive_keywords = [
            "happy",
            "joyful",
            "cheerful",
            "uplifting",
            "fun",
            "bright",
        ]
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
        acoustic_keywords = [
            "acoustic",
            "unplugged",
            "organic",
            "folk",
            "singer-songwriter",
        ]
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

    def _parse_llm_response_fallback(
        self, response_content: Union[str, AIMessage]
    ) -> Dict[str, Any]:
        """Parse LLM response when JSON parsing fails.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed mood analysis
        """
        content = (
            response_content
            if isinstance(response_content, str)
            else response_content.content
        )
        content_lower = content.lower()

        analysis = {
            "mood_interpretation": content[:200] + "...",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "search_keywords": [],
            "reasoning": content,
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
