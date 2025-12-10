"""Mood analyzer agent for understanding user mood prompts."""

from typing import Optional

import structlog
from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from .analysis import MoodAnalysisEngine
from .features import FeatureExtractor
from .planning import PlaylistTargetPlanner
from .text import KeywordExtractor

logger = structlog.get_logger(__name__)


class MoodAnalyzerAgent(BaseAgent):
    """Agent for analyzing and understanding user mood prompts."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        spotify_service=None,
        reccobeat_service=None,
        verbose: bool = False,
    ):
        """Initialize the mood analyzer agent.

        Args:
            llm: Language model for mood analysis
            spotify_service: SpotifyService (kept for backward compatibility)
            reccobeat_service: RecoBeatService (kept for backward compatibility)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="mood_analyzer",
            description="Analyzes user mood prompts and translates them into audio features",
            llm=llm,
            verbose=verbose,
        )

        # Note: spotify_service and reccobeat_service kept for backward compatibility
        # but no longer used by this agent (moved to SeedGathererAgent)

        # Initialize component classes
        self.mood_analysis_engine = MoodAnalysisEngine(llm=llm)
        self.feature_extractor = FeatureExtractor()
        self.playlist_target_planner = PlaylistTargetPlanner()
        self.keyword_extractor = KeywordExtractor()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute mood analysis on the user's prompt.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with mood analysis
        """
        try:
            logger.info(f"Analyzing mood prompt: {state.mood_prompt}")

            # Update state
            state.current_step = "analyzing_mood"
            state.status = RecommendationStatus.ANALYZING_MOOD
            await self._notify_progress(state)

            # STEP 1: Perform mood analysis
            mood_analysis = await self._perform_mood_analysis(state)

            # STEP 2: Extract and store features
            await self._extract_and_store_features(state, mood_analysis)

            # STEP 3: Determine playlist target
            await self._determine_playlist_target(state, mood_analysis)

            logger.info("Mood analysis completed (focused on audio features)")

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state

    async def _perform_mood_analysis(self, state: AgentState) -> dict:
        """Perform mood analysis to extract audio features.

        Args:
            state: Current agent state

        Returns:
            Mood analysis dictionary
        """
        logger.info("Performing mood analysis for audio features")

        # Perform mood analysis
        mood_analysis = await self.mood_analysis_engine.analyze_mood(state.mood_prompt)

        # BUGFIX: DO NOT filter out user-mentioned artists from recommendations
        # Both UserAnchorStrategy AND ArtistDiscovery should process user-mentioned artists
        # This provides redundancy - if one fails, the other can still get tracks
        # The diversity manager will handle deduplication if needed
        intent_analysis = state.metadata.get("intent_analysis", {})
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])

        if user_mentioned_artists:
            logger.info(
                f"User mentioned {len(user_mentioned_artists)} artist(s): {', '.join(user_mentioned_artists)}. "
                f"These will be processed by BOTH UserAnchorStrategy and ArtistDiscovery for redundancy."
            )

        # Update state with analysis
        state.mood_analysis = mood_analysis

        logger.info(
            f"Mood analysis: {len(mood_analysis.get('genre_keywords', []))} genres, "
            f"primary emotion: {mood_analysis.get('primary_emotion', 'unknown')}"
        )

        return mood_analysis

    async def _extract_and_store_features(
        self, state: AgentState, mood_analysis: dict
    ) -> None:
        """Extract target features and weights from mood analysis.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis dictionary
        """
        # Extract target features and weights using feature extractor
        target_features = self.feature_extractor.extract_target_features(mood_analysis)
        feature_weights = self.feature_extractor.extract_feature_weights(mood_analysis)

        # Store in metadata for use by other agents
        if "target_features" not in state.metadata:
            state.metadata["target_features"] = {}
        if "feature_weights" not in state.metadata:
            state.metadata["feature_weights"] = {}

        state.metadata["target_features"].update(target_features)
        state.metadata["feature_weights"].update(feature_weights)

        # Also store mood analysis details for reference
        state.metadata["mood_interpretation"] = mood_analysis.get(
            "mood_interpretation", ""
        )
        state.metadata["primary_emotion"] = mood_analysis.get(
            "primary_emotion", "neutral"
        )
        state.metadata["search_keywords"] = mood_analysis.get("search_keywords", [])
        state.metadata["artist_recommendations"] = mood_analysis.get(
            "artist_recommendations", []
        )
        state.metadata["genre_keywords"] = mood_analysis.get("genre_keywords", [])

        logger.info(f"Target features: {list(target_features.keys())}")
        logger.info(f"Feature weights: {feature_weights}")

    async def _determine_playlist_target(
        self, state: AgentState, mood_analysis: dict
    ) -> None:
        """Determine playlist target plan based on mood.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis dictionary
        """
        target_features = state.metadata.get("target_features", {})

        playlist_target = self.playlist_target_planner.determine_playlist_target(
            state.mood_prompt, mood_analysis, target_features
        )
        state.metadata["playlist_target"] = playlist_target

        logger.info(
            f"Playlist target: {playlist_target['target_count']} tracks "
            f"(min: {playlist_target['min_count']}) - "
            f"{playlist_target['reasoning']}"
        )
