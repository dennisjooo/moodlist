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
from .anchor_track_selector import AnchorTrackSelector

logger = structlog.get_logger(__name__)


class MoodAnalyzerAgent(BaseAgent):
    """Agent for analyzing and understanding user mood prompts."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        spotify_service=None,
        reccobeat_service=None,
        verbose: bool = False
    ):
        """Initialize the mood analyzer agent.

        Args:
            llm: Language model for mood analysis
            spotify_service: SpotifyService for artist discovery
            reccobeat_service: RecoBeatService for audio features (anchor tracks)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="mood_analyzer",
            description="Analyzes user mood prompts and translates them into audio features and search parameters",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

        # Initialize component classes
        self.mood_analysis_engine = MoodAnalysisEngine(llm=llm)
        self.feature_extractor = FeatureExtractor()
        self.artist_discovery = ArtistDiscovery(spotify_service=spotify_service, llm=llm)
        self.playlist_target_planner = PlaylistTargetPlanner()
        self.keyword_extractor = KeywordExtractor()
        self.anchor_track_selector = AnchorTrackSelector(
            spotify_service=spotify_service,
            reccobeat_service=reccobeat_service,
            llm=llm
        )

    async def execute(self, state: AgentState) -> AgentState:
        """Execute mood analysis on the user's prompt.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with mood analysis
        """
        try:
            logger.info(f"Analyzing mood prompt: {state.mood_prompt}")

            # Perform mood analysis
            mood_analysis = await self._perform_mood_analysis(state)
            
            # Extract and store features
            await self._extract_and_store_features(state, mood_analysis)
            
            # Determine playlist target
            await self._determine_playlist_target(state, mood_analysis)
            
            # Discover artists
            await self._discover_artists(state, mood_analysis)
            
            # Select anchor tracks
            await self._select_anchor_tracks(state, mood_analysis)

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state

    async def _perform_mood_analysis(self, state: AgentState) -> dict:
        """Perform comprehensive mood analysis.
        
        Args:
            state: Current agent state
            
        Returns:
            Mood analysis dictionary
        """
        mood_analysis = await self.mood_analysis_engine.analyze_mood(state.mood_prompt)

        # Update state with analysis
        state.mood_analysis = mood_analysis
        state.current_step = "mood_analyzed"
        state.status = RecommendationStatus.ANALYZING_MOOD

        logger.info(f"Mood analysis completed for prompt: {state.mood_prompt}")
        
        return mood_analysis

    async def _extract_and_store_features(self, state: AgentState, mood_analysis: dict) -> None:
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
        state.metadata["mood_interpretation"] = mood_analysis.get("mood_interpretation", "")
        state.metadata["primary_emotion"] = mood_analysis.get("primary_emotion", "neutral")
        state.metadata["search_keywords"] = mood_analysis.get("search_keywords", [])
        state.metadata["artist_recommendations"] = mood_analysis.get("artist_recommendations", [])
        state.metadata["genre_keywords"] = mood_analysis.get("genre_keywords", [])

        logger.info(f"Target features: {list(target_features.keys())}")
        logger.info(f"Feature weights: {feature_weights}")

    async def _determine_playlist_target(self, state: AgentState, mood_analysis: dict) -> None:
        """Determine playlist target plan based on mood.
        
        Args:
            state: Current agent state
            mood_analysis: Mood analysis dictionary
        """
        target_features = state.metadata.get("target_features", {})
        
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

    async def _discover_artists(self, state: AgentState, mood_analysis: dict) -> None:
        """Discover artists matching the mood.
        
        Args:
            state: Current agent state
            mood_analysis: Mood analysis dictionary
        """
        if self.spotify_service:
            await self.artist_discovery.discover_mood_artists(state, mood_analysis)

    async def _select_anchor_tracks(self, state: AgentState, mood_analysis: dict) -> None:
        """Select anchor tracks (user-mentioned tracks + genre-based tracks).
        
        Args:
            state: Current agent state
            mood_analysis: Mood analysis dictionary
        """
        if not self.spotify_service:
            return

        try:
            target_features = state.metadata.get("target_features", {})
            
            anchor_tracks, anchor_ids = await self.anchor_track_selector.select_anchor_tracks(
                mood_analysis.get("genre_keywords", []),
                target_features,
                state.metadata.get("spotify_access_token"),
                mood_prompt=state.mood_prompt,
                artist_recommendations=mood_analysis.get("artist_recommendations", []),
                limit=5
            )
            state.metadata["anchor_tracks"] = anchor_tracks
            state.metadata["anchor_track_ids"] = anchor_ids
            logger.info(f"Selected {len(anchor_tracks)} anchor tracks (user-mentioned + genre search)")
        except Exception as e:
            logger.warning(f"Failed to select anchor tracks: {e}")
            # Continue without anchor tracks - not critical
            state.metadata["anchor_tracks"] = []
            state.metadata["anchor_track_ids"] = []