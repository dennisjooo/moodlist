"""Intent analyzer agent for understanding user intent.

Refactored for better separation of concerns.
"""

import structlog
from typing import Optional, Dict, Any

from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ..utils.llm_response_parser import LLMResponseParser
from .prompts import get_intent_analysis_prompt
from .intent_validator import IntentValidator
from .intent_fallback import IntentFallbackAnalyzer

logger = structlog.get_logger(__name__)


class IntentAnalyzerAgent(BaseAgent):
    """Agent for analyzing user intent before generating recommendations."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        verbose: bool = False
    ):
        """Initialize the intent analyzer agent.

        Args:
            llm: Language model for intent analysis
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="intent_analyzer",
            description="Analyzes user intent to understand what kind of playlist they want",
            llm=llm,
            verbose=verbose
        )

        self.response_parser = LLMResponseParser()
        self.validator = IntentValidator()
        self.fallback_analyzer = IntentFallbackAnalyzer()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute intent analysis on the user's prompt.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with intent analysis
        """
        try:
            logger.info(f"Analyzing intent for prompt: {state.mood_prompt}")

            # Update state
            state.current_step = "analyzing_intent"
            state.status = RecommendationStatus.ANALYZING_MOOD
            await self._notify_progress(state)

            # Perform intent analysis
            if self.llm:
                intent_data = await self._analyze_intent_with_llm(state.mood_prompt)
            else:
                intent_data = self.fallback_analyzer.analyze_intent_fallback(state.mood_prompt)

            # Store intent analysis in state metadata
            state.metadata["intent_analysis"] = intent_data

            # Log the analysis
            logger.info(
                "Intent analysis completed",
                intent_type=intent_data.get("intent_type"),
                primary_genre=intent_data.get("primary_genre"),
                genre_strictness=intent_data.get("genre_strictness"),
                mentioned_tracks_count=len(intent_data.get("user_mentioned_tracks", [])),
                mentioned_artists_count=len(intent_data.get("user_mentioned_artists", []))
            )

            # Log user mentions for debugging
            if intent_data.get("user_mentioned_tracks"):
                for track in intent_data["user_mentioned_tracks"]:
                    logger.info(
                        f"User mentioned track: '{track['track_name']}' by {track['artist_name']} "
                        f"(priority: {track.get('priority', 'medium')})"
                    )

            if intent_data.get("user_mentioned_artists"):
                logger.info(f"User mentioned artists: {', '.join(intent_data['user_mentioned_artists'])}")

        except Exception as e:
            logger.error(f"Error in intent analysis: {str(e)}", exc_info=True)
            state.set_error(f"Intent analysis failed: {str(e)}")

        return state

    async def _analyze_intent_with_llm(self, mood_prompt: str) -> Dict[str, Any]:
        """Analyze intent using LLM.

        Args:
            mood_prompt: User's mood description

        Returns:
            Intent analysis dictionary
        """
        try:
            prompt = get_intent_analysis_prompt(mood_prompt)

            # Call LLM
            response = await self.llm.ainvoke(prompt)

            # Parse response
            intent_data = self.response_parser.extract_json_from_response(
                response,
                fallback={
                    "intent_type": "mood_variety",
                    "user_mentioned_tracks": [],
                    "user_mentioned_artists": [],
                    "primary_genre": None,
                    "genre_strictness": 0.6,
                    "language_preferences": ["english"],
                    "exclude_regions": [],
                    "allow_obscure_artists": False,
                    "quality_threshold": 0.6,
                    "reasoning": "Failed to parse LLM response"
                }
            )

            # Validate and sanitize the parsed data
            intent_data = self.validator.validate_intent_data(intent_data)

            logger.info(f"LLM intent analysis: {intent_data.get('reasoning', 'No reasoning provided')}")

            return intent_data

        except Exception as e:
            logger.error(f"Error in LLM intent analysis: {e}", exc_info=True)
            # Fallback to rule-based
            return self.fallback_analyzer.analyze_intent_fallback(mood_prompt)

