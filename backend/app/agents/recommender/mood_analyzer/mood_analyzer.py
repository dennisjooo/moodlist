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

            # STEP 1: Get initial mood understanding to extract genres/artists
            initial_analysis = await self._perform_initial_analysis(state)
            
            # STEP 2: Select anchor tracks FIRST using initial genres
            await self._select_anchor_tracks_early(state, initial_analysis)
            
            # STEP 3: Discover artists using initial analysis and anchor tracks
            await self._discover_artists_with_anchors(state, initial_analysis)
            
            # STEP 4: Perform full mood analysis with anchor context
            mood_analysis = await self._perform_mood_analysis_with_anchors(state, initial_analysis)
            
            # STEP 5: Extract and store features
            await self._extract_and_store_features(state, mood_analysis)
            
            # STEP 6: Determine playlist target
            await self._determine_playlist_target(state, mood_analysis)

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state

    async def _perform_initial_analysis(self, state: AgentState) -> dict:
        """Perform initial lightweight mood analysis to extract genres and artists.
        
        Args:
            state: Current agent state
            
        Returns:
            Initial analysis dictionary with genres and artist hints
        """
        logger.info("Performing initial analysis to extract genres and artists")
        
        # Use the same mood analysis engine but we'll use it as initial pass
        initial_analysis = await self.mood_analysis_engine.analyze_mood(state.mood_prompt)
        
        logger.info(
            f"Initial analysis: {len(initial_analysis.get('genre_keywords', []))} genres, "
            f"{len(initial_analysis.get('artist_recommendations', []))} artist hints"
        )
        
        return initial_analysis

    async def _perform_mood_analysis_with_anchors(self, state: AgentState, initial_analysis: dict) -> dict:
        """Perform comprehensive mood analysis informed by anchor tracks.
        
        Args:
            state: Current agent state
            initial_analysis: Initial analysis from first pass
            
        Returns:
            Full mood analysis dictionary
        """
        logger.info("Performing full mood analysis with anchor track context")
        
        # Get anchor track info for context
        anchor_tracks = state.metadata.get("anchor_tracks", [])
        anchor_info = ""
        if anchor_tracks:
            track_list = [f"{t.get('name', '')} by {t.get('artist', '')}" for t in anchor_tracks[:3]]
            anchor_info = f"\n\nReference tracks found: {', '.join(track_list)}"
        
        # Perform full analysis (could be enhanced to use anchor_info in prompt)
        mood_analysis = await self.mood_analysis_engine.analyze_mood(
            state.mood_prompt + anchor_info
        )
        
        # Merge with initial analysis if needed
        mood_analysis["genre_keywords"] = initial_analysis.get("genre_keywords", [])
        mood_analysis["artist_recommendations"] = initial_analysis.get("artist_recommendations", [])

        # Update state with analysis
        state.mood_analysis = mood_analysis
        state.current_step = "mood_analyzed"
        state.status = RecommendationStatus.ANALYZING_MOOD

        logger.info(f"Full mood analysis completed with anchor context")
        
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

    async def _select_anchor_tracks_early(self, state: AgentState, initial_analysis: dict) -> None:
        """Select anchor tracks EARLY using initial genre analysis.
        
        This happens BEFORE full mood analysis to provide reference tracks.
        
        Args:
            state: Current agent state
            initial_analysis: Initial analysis with genres and artist hints
        """
        if not self.spotify_service:
            return

        try:
            # Use basic target features for early anchor selection
            # We don't have full features yet, so use initial analysis hints
            basic_target_features = self._extract_basic_features(initial_analysis)
            
            anchor_tracks, anchor_ids = await self.anchor_track_selector.select_anchor_tracks(
                initial_analysis.get("genre_keywords", []),
                basic_target_features,
                state.metadata.get("spotify_access_token"),
                mood_prompt=state.mood_prompt,
                artist_recommendations=initial_analysis.get("artist_recommendations", []),
                limit=5
            )
            state.metadata["anchor_tracks"] = anchor_tracks
            state.metadata["anchor_track_ids"] = anchor_ids
            logger.info(f"✓ Selected {len(anchor_tracks)} anchor tracks early (before full mood analysis)")
        except Exception as e:
            logger.warning(f"Failed to select anchor tracks early: {e}")
            # Continue without anchor tracks - not critical
            state.metadata["anchor_tracks"] = []
            state.metadata["anchor_track_ids"] = []

    async def _discover_artists_with_anchors(self, state: AgentState, initial_analysis: dict) -> None:
        """Discover artists using initial analysis and anchor track context.
        
        Args:
            state: Current agent state
            initial_analysis: Initial analysis dictionary
        """
        if not self.spotify_service:
            return
            
        logger.info("Discovering artists with anchor track context")
        
        # Use initial analysis for artist discovery
        await self.artist_discovery.discover_mood_artists(state, initial_analysis)
        
        # Extract artists from anchor tracks and add to discovered artists
        anchor_tracks = state.metadata.get("anchor_tracks", [])
        if anchor_tracks:
            anchor_artists = []
            for track in anchor_tracks:
                artist_name = track.get("artist")
                artist_id = track.get("artist_id")
                if artist_name and artist_id:
                    anchor_artists.append({
                        "id": artist_id,
                        "name": artist_name,
                        "popularity": track.get("popularity", 50),
                        "source": "anchor_track"
                    })
            
            if anchor_artists:
                discovered_artists = state.metadata.get("discovered_artists", [])
                # Add anchor artists but avoid duplicates
                existing_ids = {a["id"] for a in discovered_artists}
                for artist in anchor_artists:
                    if artist["id"] not in existing_ids:
                        discovered_artists.append(artist)
                        existing_ids.add(artist["id"])
                
                state.metadata["discovered_artists"] = discovered_artists
                logger.info(f"Added {len(anchor_artists)} artists from anchor tracks")

    def _extract_basic_features(self, initial_analysis: dict) -> dict:
        """Extract basic target features from initial analysis.
        
        Args:
            initial_analysis: Initial analysis dictionary
            
        Returns:
            Basic target features dictionary
        """
        # Use feature extractor with initial analysis
        return self.feature_extractor.extract_target_features(initial_analysis)