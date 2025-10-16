"""Mood analysis engine for LLM-based and fallback mood analysis."""

import logging
from typing import Any, Dict, Optional, Union, List

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import AIMessage

from ..utils import LLMResponseParser, config
from .prompts import get_mood_analysis_system_prompt
from .text_processor import TextProcessor
from .mood_profile_matcher import MoodProfileMatcher

logger = logging.getLogger(__name__)


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
                {"role": "user", "content": f"Analyze this mood: '{mood_prompt}'"}
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Parse JSON response using centralized parser
            analysis = LLMResponseParser.extract_json_from_response(response)

            if not analysis:
                # Fallback if JSON parsing fails
                content = response.content if hasattr(response, 'content') else str(response)
                logger.warning("Could not parse JSON from LLM mood analysis response")
                analysis = self._parse_llm_response_fallback(content)

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

        # Match and apply mood profiles
        matched_profiles = self._profile_matcher.match_mood_profiles(mood_prompt)
        self._profile_matcher.apply_mood_profiles(matched_profiles, mood_prompt, analysis)

        # Additional keyword-based feature analysis
        self._enhance_features_with_keywords(analysis, prompt_lower)

        # Generate search keywords
        analysis["search_keywords"] = self._text_processor.extract_search_keywords(mood_prompt)

        # Extract genre keywords and artist recommendations
        genre_keywords, artist_recommendations = self._text_processor.extract_genres_and_artists(mood_prompt)
        analysis["genre_keywords"] = genre_keywords
        analysis["artist_recommendations"] = artist_recommendations

        return analysis

    def _enhance_features_with_keywords(self, analysis: Dict[str, Any], prompt_lower: str):
        """Enhance feature analysis with specific keywords using data-driven approach."""
        # Define keyword-to-feature mappings
        keyword_mappings = self._get_keyword_feature_mappings()

        # Apply each mapping
        for mapping in keyword_mappings:
            self._apply_keyword_mapping(analysis, prompt_lower, mapping)

    def _get_keyword_feature_mappings(self) -> List[Dict[str, Any]]:
        """Get data-driven keyword to feature mappings from centralized config."""
        return config.keyword_feature_mappings

    def _apply_keyword_mapping(
        self,
        analysis: Dict[str, Any],
        prompt_lower: str,
        mapping: Dict[str, Any]
    ) -> None:
        """Apply a single keyword-to-feature mapping."""
        keywords = mapping["keywords"]

        # Check if any keywords match
        if any(keyword in prompt_lower for keyword in keywords):
            # Set emotion/energy level if specified
            if "emotion_level" in mapping:
                level_key, level_value = mapping["emotion_level"]
                analysis[level_key] = level_value

            # Apply feature ranges (only if not already set)
            for feature_name, feature_range in mapping["features"].items():
                if feature_name not in analysis["target_features"]:
                    analysis["target_features"][feature_name] = feature_range

    def _parse_llm_response_fallback(self, response_content: Union[str, AIMessage]) -> Dict[str, Any]:
        """Parse LLM response when JSON parsing fails.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed mood analysis
        """
        content = response_content if isinstance(response_content, str) else response_content.content
        content_lower = content.lower() 

        analysis = {
            "mood_interpretation": content[:200] + "...",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "search_keywords": [],
            "reasoning": content
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
