"""Intent analyzer agent for understanding user intent."""

import structlog
from typing import Optional, Dict, Any, List

from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ..utils.llm_response_parser import LLMResponseParser
from .prompts import get_intent_analysis_prompt

logger = structlog.get_logger(__name__)

INTENT_PATTERNS = {
    "specific_track_similar": ["like ", "similar to", "things like"],
    "artist_focus": ["playlist", "give me", "only"],
    "genre_exploration": ["explore", "discover", "variety", "mix"],
}

GENRE_KEYWORDS = {
    "trap": ["trap", "travis scott", "future", "migos"],
    "hip hop": ["hip hop", "rap", "rapper"],
    "pop": ["pop", "taylor swift", "ariana"],
    "rock": ["rock", "indie", "alternative"],
    "electronic": ["electronic", "edm", "techno", "house"],
    "jazz": ["jazz", "bebop", "swing"],
    "classical": ["classical", "orchestra", "symphony"],
    "country": ["country", "nashville"],
    "funk": ["funk", "funky"],
    "soul": ["soul", "r&b", "rnb"],
}

GENRE_STRICTNESS = {
    "artist_focus": 0.85,
    "specific_track_similar": 0.85,
    "genre_exploration": 0.7,
    "mood_variety": 0.6,
}

VALID_INTENT_TYPES = set(GENRE_STRICTNESS)


def _default_intent_data() -> Dict[str, Any]:
    return {
        "intent_type": "mood_variety",
        "user_mentioned_tracks": [],
        "user_mentioned_artists": [],
        "primary_genre": None,
        "genre_strictness": GENRE_STRICTNESS["mood_variety"],
        "language_preferences": ["english"],
        "exclude_regions": [],
        "allow_obscure_artists": False,
        "quality_threshold": 0.6,
        "reasoning": "Fallback rule-based analysis",
    }


def _coerce_list(value: Any, default: List[Any]) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    return list(default)


def _coerce_float(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _sanitize_tracks(tracks: Any) -> List[Dict[str, Any]]:
    if not isinstance(tracks, list):
        return []

    sanitized = []
    for track in tracks:
        if isinstance(track, dict) and track.get("track_name") and track.get("artist_name"):
            sanitized.append(
                {
                    "track_name": str(track["track_name"]),
                    "artist_name": str(track["artist_name"]),
                    "priority": track.get("priority", "medium")
                    if track.get("priority") in {"high", "medium"}
                    else "medium",
                }
            )
    return sanitized


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
                intent_data = self._analyze_intent_fallback(state.mood_prompt)

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

            response = await self.llm.ainvoke(prompt)
            intent_data = self.response_parser.extract_json_from_response(
                response, fallback=_default_intent_data()
            )
            intent_data = self._validate_intent_data(intent_data)

            logger.info(f"LLM intent analysis: {intent_data.get('reasoning', 'No reasoning provided')}")

            return intent_data

        except Exception as e:
            logger.error(f"Error in LLM intent analysis: {e}", exc_info=True)
            # Fallback to rule-based
            return self._analyze_intent_fallback(mood_prompt)

    def _analyze_intent_fallback(self, mood_prompt: str) -> Dict[str, Any]:
        """Fallback intent analysis using rule-based approach.

        Args:
            mood_prompt: User's mood description

        Returns:
            Basic intent analysis dictionary
        """
        mood_lower = mood_prompt.lower()

        intent_type = "mood_variety"
        for candidate, patterns in INTENT_PATTERNS.items():
            if any(p in mood_lower for p in patterns):
                intent_type = candidate
                break

        primary_genre = next(
            (
                genre
                for genre, keywords in GENRE_KEYWORDS.items()
                if any(keyword in mood_lower for keyword in keywords)
            ),
            None,
        )

        intent_data = _default_intent_data()
        intent_data.update(
            {
                "intent_type": intent_type,
                "primary_genre": primary_genre,
                "genre_strictness": GENRE_STRICTNESS[intent_type],
            }
        )

        logger.info(f"Fallback intent analysis: {intent_type}, genre: {primary_genre}")
        return intent_data

    def _validate_intent_data(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize intent data from LLM.

        Args:
            intent_data: Raw intent data from LLM

        Returns:
            Validated intent data
        """
        if intent_data.get("intent_type") not in VALID_INTENT_TYPES:
            logger.warning(f"Invalid intent_type '{intent_data.get('intent_type')}', defaulting to 'mood_variety'")
            intent_data["intent_type"] = "mood_variety"

        intent_data["user_mentioned_tracks"] = _sanitize_tracks(intent_data.get("user_mentioned_tracks"))
        intent_data["user_mentioned_artists"] = _coerce_list(intent_data.get("user_mentioned_artists"), [])
        intent_data["language_preferences"] = _coerce_list(
            intent_data.get("language_preferences"), ["english"]
        )
        intent_data["exclude_regions"] = _coerce_list(intent_data.get("exclude_regions"), [])
        intent_data["genre_strictness"] = _coerce_float(intent_data.get("genre_strictness"), 0.6)
        intent_data["quality_threshold"] = _coerce_float(intent_data.get("quality_threshold"), 0.6)
        intent_data["allow_obscure_artists"] = _coerce_bool(intent_data.get("allow_obscure_artists"), False)

        return intent_data

