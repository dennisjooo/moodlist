"""Mood analyzer agent for understanding user mood prompts."""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.agent_tools import ToolResult


logger = logging.getLogger(__name__)


class MoodAnalyzerAgent(BaseAgent):
    """Agent for analyzing and understanding user mood prompts."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        verbose: bool = False
    ):
        """Initialize the mood analyzer agent.

        Args:
            llm: Language model for mood analysis
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="mood_analyzer",
            description="Analyzes user mood prompts and translates them into audio features and search parameters",
            llm=llm,
            verbose=verbose
        )

        # Mood analysis prompts
        self.system_prompt = """You are an expert music curator and mood analyst. Your task is to analyze user mood prompts and translate them into specific audio features and search parameters for music recommendations.

Analyze the user's mood description and provide:
1. A clear interpretation of their desired mood
2. Specific audio features that match the mood
3. Keywords for searching relevant artists
4. Reasoning for your choices

Focus on these audio features:
- Energy: 0-1 (0=calm/relaxed, 1=intense/powerful)
- Valence: 0-1 (0=sad/negative, 1=happy/positive)
- Danceability: 0-1 (0=not danceable, 1=very danceable)
- Acousticness: 0-1 (0=electronic/synthetic, 1=acoustic/natural)
- Instrumentalness: 0-1 (0=likely vocal, 1=likely instrumental)
- Tempo: BPM range (0-250)
- Mode: 0=minor (sadder), 1=major (happier)

Provide your analysis in valid JSON format."""

    async def execute(self, state: AgentState) -> AgentState:
        """Execute mood analysis on the user's prompt.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with mood analysis
        """
        try:
            logger.info(f"Analyzing mood prompt: {state.mood_prompt}")

            # Use LLM for mood analysis
            if self.llm:
                mood_analysis = await self._analyze_mood_with_llm(state.mood_prompt)
            else:
                # Fallback rule-based analysis
                mood_analysis = self._analyze_mood_fallback(state.mood_prompt)

            # Update state with analysis
            state.mood_analysis = mood_analysis
            state.current_step = "mood_analyzed"
            state.status = RecommendationStatus.ANALYZING_MOOD

            # Extract target features for recommendations
            target_features = self._extract_target_features(mood_analysis)
            if "target_features" not in state.metadata:
                state.metadata["target_features"] = {}
            state.metadata["target_features"].update(target_features)

            logger.info(f"Mood analysis completed for prompt: {state.mood_prompt}")
            logger.info(f"Target features: {target_features}")

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state

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
                {"role": "system", "content": self.system_prompt},
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
                analysis = self._parse_llm_response_fallback(response)

            return analysis

        except Exception as e:
            logger.error(f"LLM mood analysis failed: {str(e)}")
            return self._analyze_mood_fallback(mood_prompt)

    def _analyze_mood_fallback(self, mood_prompt: str) -> Dict[str, Any]:
        """Fallback rule-based mood analysis.

        Args:
            mood_prompt: User's mood description

        Returns:
            Basic mood analysis
        """
        prompt_lower = mood_prompt.lower()

        # Simple keyword-based analysis
        analysis = {
            "mood_interpretation": f"Mood based on: {mood_prompt}",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "search_keywords": [],
            "reasoning": f"Rule-based analysis of prompt: {mood_prompt}"
        }

        # Energy analysis
        high_energy_keywords = ["energetic", "upbeat", "exciting", "party", "workout", "intense", "powerful"]
        low_energy_keywords = ["calm", "relaxed", "chill", "peaceful", "sleepy", "mellow", "soft"]

        if any(keyword in prompt_lower for keyword in high_energy_keywords):
            analysis["energy_level"] = "high"
            analysis["target_features"]["energy"] = [0.7, 1.0]
            analysis["target_features"]["valence"] = [0.6, 1.0]
        elif any(keyword in prompt_lower for keyword in low_energy_keywords):
            analysis["energy_level"] = "low"
            analysis["target_features"]["energy"] = [0.0, 0.4]
            analysis["target_features"]["acousticness"] = [0.5, 1.0]

        # Valence analysis
        positive_keywords = ["happy", "joyful", "cheerful", "positive", "uplifting", "fun"]
        negative_keywords = ["sad", "melancholy", "depressed", "dark", "moody", "emotional"]

        if any(keyword in prompt_lower for keyword in positive_keywords):
            analysis["primary_emotion"] = "positive"
            analysis["target_features"]["valence"] = [0.7, 1.0]
        elif any(keyword in prompt_lower for keyword in negative_keywords):
            analysis["primary_emotion"] = "negative"
            analysis["target_features"]["valence"] = [0.0, 0.4]

        # Danceability analysis
        dance_keywords = ["dance", "dancing", "club", "party", "groove", "rhythm"]
        if any(keyword in prompt_lower for keyword in dance_keywords):
            analysis["target_features"]["danceability"] = [0.7, 1.0]

        # Acousticness analysis
        acoustic_keywords = ["acoustic", "unplugged", "natural", "organic", "folk"]
        if any(keyword in prompt_lower for keyword in acoustic_keywords):
            analysis["target_features"]["acousticness"] = [0.7, 1.0]

        # Generate search keywords
        analysis["search_keywords"] = self._extract_search_keywords(mood_prompt)

        return analysis

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

    def _extract_target_features(self, mood_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract target audio features from mood analysis.

        Args:
            mood_analysis: Comprehensive mood analysis

        Returns:
            Dictionary of target audio features
        """
        target_features = {}

        features = mood_analysis.get("target_features", {})

        # Convert ranges to target values (use midpoint)
        for feature, value_range in features.items():
            if isinstance(value_range, list) and len(value_range) == 2:
                target_features[feature] = sum(value_range) / 2
            elif isinstance(value_range, (int, float)):
                target_features[feature] = float(value_range)

        return target_features

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