"""Seed gatherer agent for collecting user preference data.

Phase 2 Refactor: This agent now handles:
- Searching for user-mentioned tracks (from intent analyzer)
- Selecting anchor tracks (moved from MoodAnalyzerAgent)
- Discovering and validating artists (moved from MoodAnalyzerAgent)
- Building optimized seed pool
"""

import structlog
from typing import Optional

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ...tools.spotify_service import SpotifyService
from .seed_selector import SeedSelector
from .audio_enricher import AudioEnricher
from .llm_seed_selector import LLMSeedSelector

# Import components moved from MoodAnalyzerAgent
from ..mood_analyzer.anchor_selection import AnchorTrackSelector
from ..mood_analyzer.discovery import ArtistDiscovery

logger = structlog.get_logger(__name__)


class SeedGathererAgent(BaseAgent):
    """Agent for gathering seed tracks and artists from user data.
    
    Phase 2: Enhanced with anchor selection and artist discovery.
    """

    def __init__(
        self,
        spotify_service: SpotifyService,
        reccobeat_service=None,
        llm=None,
        verbose: bool = False
    ):
        """Initialize the seed gatherer agent.

        Args:
            spotify_service: Service for Spotify API operations
            reccobeat_service: Service for RecoBeat API operations (for audio features)
            llm: Language model for intelligent seed selection
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="seed_gatherer",
            description="Gathers seeds, searches user-mentioned tracks, selects anchors, discovers artists",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

        # Initialize component modules
        self.seed_selector = SeedSelector()
        self.audio_enricher = AudioEnricher(reccobeat_service)
        self.llm_seed_selector = LLMSeedSelector(llm)
        
        # Phase 2: Components moved from MoodAnalyzerAgent
        self.anchor_track_selector = AnchorTrackSelector(
            spotify_service=spotify_service,
            reccobeat_service=reccobeat_service,
            llm=llm
        )
        self.artist_discovery = ArtistDiscovery(
            spotify_service=spotify_service,
            llm=llm
        )

    async def execute(self, state: AgentState) -> AgentState:
        """Execute seed gathering with Phase 2 enhancements.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with seed data
        """
        try:
            logger.info(f"Gathering seeds for user {state.user_id} (Phase 2)")

            # Check if we have Spotify access token
            if not hasattr(state, 'access_token') or not state.access_token:
                # Try to get from metadata or user record
                access_token = state.metadata.get("spotify_access_token")
                if not access_token:
                    raise ValueError("No Spotify access token available for seed gathering")

            # Get intent analysis from state (set by IntentAnalyzerAgent)
            intent_analysis = state.metadata.get("intent_analysis", {})
            
            # Phase 2 STEP 1: Search for user-mentioned tracks
            await self._search_user_mentioned_tracks(state, intent_analysis, access_token)
            
            # Phase 2 STEP 2: Select anchor tracks
            await self._select_anchor_tracks(state, intent_analysis, access_token)
            
            # Phase 2 STEP 3: Discover and validate artists
            await self._discover_and_validate_artists(state, intent_analysis, access_token)
            
            # STEP 4: Get user's top tracks for additional seeds
            state.current_step = "gathering_seeds_fetching_top_tracks"
            await self._notify_progress(state)
            
            top_tracks = await self.spotify_service.get_user_top_tracks(
                access_token=access_token,
                limit=20,
                time_range="medium_term"
            )

            # STEP 5: Get user's top artists for additional context
            state.current_step = "gathering_seeds_fetching_top_artists"
            await self._notify_progress(state)
            
            top_artists = await self.spotify_service.get_user_top_artists(
                access_token=access_token,
                limit=15,
                time_range="medium_term"
            )

            # STEP 6: Build optimized seed pool
            await self._build_seed_pool(state, top_tracks, top_artists, access_token)

            # Update state
            state.current_step = "seeds_gathered"
            state.status = RecommendationStatus.GATHERING_SEEDS

            logger.info("Seed gathering completed (Phase 2)")

        except Exception as e:
            logger.error(f"Error in seed gathering: {str(e)}", exc_info=True)
            state.set_error(f"Seed gathering failed: {str(e)}")

        return state

    async def _search_user_mentioned_tracks(
        self,
        state: AgentState,
        intent_analysis: dict,
        access_token: str
    ) -> None:
        """Search for tracks explicitly mentioned by the user.
        
        Phase 2: New functionality to find user-mentioned tracks.
        
        Args:
            state: Current agent state
            intent_analysis: Intent analysis from IntentAnalyzerAgent
            access_token: Spotify access token
        """
        user_mentioned_tracks = intent_analysis.get("user_mentioned_tracks", [])
        
        if not user_mentioned_tracks:
            logger.info("No user-mentioned tracks to search for")
            state.metadata["user_mentioned_track_ids"] = []
            state.metadata["user_mentioned_tracks_full"] = []
            return

        logger.info(f"Searching for {len(user_mentioned_tracks)} user-mentioned tracks")
        state.current_step = "gathering_seeds_searching_user_tracks"
        await self._notify_progress(state)

        found_tracks = []
        found_track_ids = []

        for track_info in user_mentioned_tracks:
            track_name = track_info.get("track_name")
            artist_name = track_info.get("artist_name")
            priority = track_info.get("priority", "medium")

            try:
                # Search Spotify for the track
                search_query = f"track:{track_name} artist:{artist_name}"
                search_results = await self.spotify_service.search_spotify_tracks(
                    access_token=access_token,
                    query=search_query,
                    limit=3
                )

                if search_results and len(search_results) > 0:
                    # Take the first result (best match)
                    track = search_results[0]
                    track_id = track.get("id")
                    
                    if track_id:
                        found_tracks.append({
                            "id": track_id,
                            "name": track.get("name"),
                            "artist": track.get("artists", [{}])[0].get("name"),
                            "artist_id": track.get("artists", [{}])[0].get("id"),
                            "uri": track.get("uri"),
                            "popularity": track.get("popularity", 50),
                            "user_mentioned": True,
                            "priority": priority,
                            "anchor_type": "user",
                            "protected": True  # User-mentioned tracks are protected
                        })
                        found_track_ids.append(track_id)
                        
                        logger.info(
                            f"✓ Found user-mentioned track: '{track.get('name')}' "
                            f"by {track.get('artists', [{}])[0].get('name')} (priority: {priority})"
                        )
                else:
                    logger.warning(f"Could not find track: '{track_name}' by {artist_name}")

            except Exception as e:
                logger.error(f"Error searching for track '{track_name}': {e}")

        # Store in state metadata
        state.metadata["user_mentioned_track_ids"] = found_track_ids
        state.metadata["user_mentioned_tracks_full"] = found_tracks
        
        logger.info(f"Found {len(found_tracks)}/{len(user_mentioned_tracks)} user-mentioned tracks")

    async def _select_anchor_tracks(
        self,
        state: AgentState,
        intent_analysis: dict,
        access_token: str
    ) -> None:
        """Select anchor tracks using mood analysis and genre keywords.
        
        Phase 2: Moved from MoodAnalyzerAgent.
        
        Args:
            state: Current agent state
            intent_analysis: Intent analysis
            access_token: Spotify access token
        """
        logger.info("Selecting anchor tracks")
        state.current_step = "gathering_seeds_selecting_anchors"
        await self._notify_progress(state)

        try:
            # Get data from state
            mood_analysis = state.mood_analysis or {}
            target_features = state.metadata.get("target_features", {})
            genre_keywords = mood_analysis.get("genre_keywords", [])
            artist_recommendations = mood_analysis.get("artist_recommendations", [])
            
            # Use intent analysis for stricter genre matching if available
            if intent_analysis.get("primary_genre"):
                genre_keywords = [intent_analysis["primary_genre"]] + genre_keywords

            anchor_tracks, anchor_ids = await self.anchor_track_selector.select_anchor_tracks(
                genre_keywords,
                target_features,
                access_token,
                mood_prompt=state.mood_prompt,
                artist_recommendations=artist_recommendations,
                mood_analysis=mood_analysis,
                limit=5
            )
            
            state.metadata["anchor_tracks"] = anchor_tracks
            state.metadata["anchor_track_ids"] = anchor_ids
            
            logger.info(f"✓ Selected {len(anchor_tracks)} anchor tracks")
            
        except Exception as e:
            logger.warning(f"Failed to select anchor tracks: {e}")
            state.metadata["anchor_tracks"] = []
            state.metadata["anchor_track_ids"] = []

    async def _discover_and_validate_artists(
        self,
        state: AgentState,
        intent_analysis: dict,
        access_token: str
    ) -> None:
        """Discover and validate artists for the mood.
        
        Phase 2: Moved from MoodAnalyzerAgent, with validation added.
        
        Args:
            state: Current agent state
            intent_analysis: Intent analysis
            access_token: Spotify access token
        """
        logger.info("Discovering artists")
        state.current_step = "gathering_seeds_discovering_artists"
        await self._notify_progress(state)

        try:
            mood_analysis = state.mood_analysis or {}
            
            # Discover artists using mood analysis
            await self.artist_discovery.discover_mood_artists(state, mood_analysis)
            
            # Add artists from user-mentioned tracks
            user_mentioned_tracks = state.metadata.get("user_mentioned_tracks_full", [])
            if user_mentioned_tracks:
                discovered_artists = state.metadata.get("discovered_artists", [])
                existing_ids = {a["id"] for a in discovered_artists}
                
                for track in user_mentioned_tracks:
                    artist_id = track.get("artist_id")
                    artist_name = track.get("artist")
                    if artist_id and artist_id not in existing_ids:
                        discovered_artists.append({
                            "id": artist_id,
                            "name": artist_name,
                            "popularity": track.get("popularity", 50),
                            "source": "user_mentioned"
                        })
                        existing_ids.add(artist_id)
                
                state.metadata["discovered_artists"] = discovered_artists
                logger.info(f"Added {len(user_mentioned_tracks)} artists from user mentions")
            
            # Add artists from anchor tracks
            anchor_tracks = state.metadata.get("anchor_tracks", [])
            if anchor_tracks:
                discovered_artists = state.metadata.get("discovered_artists", [])
                existing_ids = {a["id"] for a in discovered_artists}
                
                for track in anchor_tracks:
                    artist_id = track.get("artist_id")
                    artist_name = track.get("artist")
                    if artist_id and artist_id not in existing_ids:
                        discovered_artists.append({
                            "id": artist_id,
                            "name": artist_name,
                            "popularity": track.get("popularity", 50),
                            "source": "anchor_track"
                        })
                        existing_ids.add(artist_id)
                
                state.metadata["discovered_artists"] = discovered_artists
                logger.info(f"Added artists from anchor tracks")

            discovered_artists = state.metadata.get("discovered_artists", [])
            logger.info(f"✓ Discovered {len(discovered_artists)} artists")
            
        except Exception as e:
            logger.error(f"Error in artist discovery: {e}", exc_info=True)
            state.metadata["discovered_artists"] = []

    async def _build_seed_pool(
        self,
        state: AgentState,
        top_tracks: list,
        top_artists: list,
        access_token: str
    ) -> None:
        """Build optimized seed pool from all sources.
        
        Args:
            state: Current agent state
            top_tracks: User's top tracks
            top_artists: User's top artists
            access_token: Spotify access token
        """
        logger.info("Building seed pool")
        state.current_step = "gathering_seeds_building_pool"
        await self._notify_progress(state)

        # Get target features and weights from metadata
        target_features = state.metadata.get("target_features", {})
        feature_weights = state.metadata.get("feature_weights", {})

        # Enhance target_features with weights
        if feature_weights:
            target_features["_weights"] = feature_weights

        # Enrich top tracks with audio features
        state.current_step = "gathering_seeds_analyzing_features"
        await self._notify_progress(state)
            
        top_tracks = await self.audio_enricher.enrich_tracks_with_features(top_tracks)

        # Select seed tracks using audio feature scoring
        state.current_step = "gathering_seeds_selecting_seeds"
        await self._notify_progress(state)
        
        scored_tracks = self.seed_selector.select_seed_tracks(top_tracks, target_features)

        # Get playlist target to determine seed count
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)

        # Calculate seed count: aim for 1 seed per 3-4 target tracks
        ideal_seed_count = max(5, min(target_count // 3, 10))

        # Use LLM to select final seeds if available
        if self.llm and len(scored_tracks) > ideal_seed_count:
            final_seeds = await self.llm_seed_selector.select_seeds(
                scored_tracks[:ideal_seed_count * 2],  # Give LLM 2x candidates
                state.mood_prompt,
                target_features,
                ideal_count=ideal_seed_count
            )
        else:
            # Just use top scored tracks
            final_seeds = scored_tracks[:ideal_seed_count]

        logger.info(
            f"Selected {len(final_seeds)} seeds for target of {target_count} tracks "
            f"(ratio: 1:{target_count // len(final_seeds) if len(final_seeds) > 0 else 1})"
        )

        state.seed_tracks = final_seeds
        state.metadata["seed_candidates_count"] = len(scored_tracks)

        # Store user's top track IDs in state for reference
        user_track_ids = [track["id"] for track in top_tracks if track.get("id")]
        state.user_top_tracks = user_track_ids

        # Extract artist IDs for context
        artist_ids = [artist["id"] for artist in top_artists if artist.get("id")]
        state.user_top_artists = artist_ids

        # Store additional metadata
        state.metadata["seed_track_count"] = len(final_seeds)
        state.metadata["user_track_count"] = len(user_track_ids)
        state.metadata["top_artist_count"] = len(artist_ids)
        state.metadata["seed_source"] = "phase2_multi_source"

        logger.info(
            f"✓ Built seed pool: {len(final_seeds)} seeds, "
            f"{len(state.metadata.get('user_mentioned_track_ids', []))} user-mentioned, "
            f"{len(state.metadata.get('anchor_track_ids', []))} anchors, "
            f"{len(state.metadata.get('discovered_artists', []))} artists"
        )
