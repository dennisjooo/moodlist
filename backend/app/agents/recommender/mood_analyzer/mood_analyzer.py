"""Mood analyzer agent for understanding user mood prompts."""

import structlog
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from . import (
    MoodAnalysisEngine,
    FeatureExtractor,
    ArtistDiscovery,
    PlaylistTargetPlanner,
    KeywordExtractor
)

logger = structlog.get_logger(__name__)


class MoodAnalyzerAgent(BaseAgent):
    """Agent for analyzing and understanding user mood prompts."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        spotify_service=None,
        verbose: bool = False
    ):
        """Initialize the mood analyzer agent.

        Args:
            llm: Language model for mood analysis
            spotify_service: SpotifyService for artist discovery
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="mood_analyzer",
            description="Analyzes user mood prompts and translates them into audio features and search parameters",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service

        # Initialize component classes
        self.mood_analysis_engine = MoodAnalysisEngine(llm=llm)
        self.feature_extractor = FeatureExtractor()
        self.artist_discovery = ArtistDiscovery(spotify_service=spotify_service, llm=llm)
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

            # Use mood analysis engine for comprehensive analysis
            mood_analysis = await self.mood_analysis_engine.analyze_mood(state.mood_prompt)

            # Update state with analysis
            state.mood_analysis = mood_analysis
            state.current_step = "mood_analyzed"
            state.status = RecommendationStatus.ANALYZING_MOOD

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
            state.metadata["mood_interpretation"] = mood_analysis.get("mood_interpretation", "")
            state.metadata["primary_emotion"] = mood_analysis.get("primary_emotion", "neutral")
            state.metadata["search_keywords"] = mood_analysis.get("search_keywords", [])
            state.metadata["artist_recommendations"] = mood_analysis.get("artist_recommendations", [])
            state.metadata["genre_keywords"] = mood_analysis.get("genre_keywords", [])

            logger.info(f"Mood analysis completed for prompt: {state.mood_prompt}")
            logger.info(f"Target features: {list(target_features.keys())}")
            logger.info(f"Feature weights: {feature_weights}")

            # Determine playlist target plan based on mood
            playlist_target = self.playlist_target_planner.determine_playlist_target(
                state.mood_prompt,
                mood_analysis,
                target_features
            )
            state.metadata["playlist_target"] = playlist_target

            logger.info(
                f"Playlist target: {playlist_target['target_count']} tracks "
                f"(min: {playlist_target['min_count']}, max: {playlist_target['max_count']}) - "
                f"{playlist_target['reasoning']}"
            )

            # Discover artists matching the mood (if Spotify service available)
            if self.spotify_service:
                await self.artist_discovery.discover_mood_artists(state, mood_analysis)

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state