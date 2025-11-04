"""Seed gatherer agent for collecting user preference data.

Phase 2 Refactor: This agent now handles:
- Searching for user-mentioned tracks (from intent analyzer)
- Selecting anchor tracks (moved from MoodAnalyzerAgent)
- Discovering and validating artists (moved from MoodAnalyzerAgent)
- Building optimized seed pool

Refactored for better separation of concerns.
"""

import time
import structlog

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ...tools.spotify_service import SpotifyService
from ...core.cache import cache_manager
from ..utils.artist_utils import ArtistDeduplicator
from ..mood_analyzer.anchor_selection import AnchorTrackSelector
from ..mood_analyzer.discovery import ArtistDiscovery
from .seed_selector import SeedSelector
from .audio_enricher import AudioEnricher
from .llm_seed_selector import LLMSeedSelector
from .user_track_searcher import UserTrackSearcher


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
        self.user_track_searcher = UserTrackSearcher(spotify_service)

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
        # Phase 1 Optimization: Track timing metrics for seed gathering
        start_time = time.time()
        timing_metrics = {}

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

            # Phase 4 Optimization: Try to reuse workflow artifacts from previous runs
            cached_artifacts = await cache_manager.get_workflow_artifacts(
                user_id=state.user_id,
                mood_prompt=state.mood_prompt
            )

            if cached_artifacts:
                logger.info("Found cached workflow artifacts, reusing data")
                state.metadata["cached_artists"] = cached_artifacts.get("artists", [])
                state.metadata["cached_anchor_tracks"] = cached_artifacts.get("anchor_tracks", [])
                state.metadata["reused_artifacts"] = True
            else:
                state.metadata["reused_artifacts"] = False

            # Phase 2 STEP 1: Search for user-mentioned tracks
            step_start = time.time()
            await self._search_user_mentioned_tracks(state, intent_analysis, access_token)
            timing_metrics["search_user_tracks"] = time.time() - step_start

            # Phase 2 STEP 2: Select anchor tracks
            step_start = time.time()
            await self._select_anchor_tracks(state, intent_analysis, access_token)
            timing_metrics["select_anchor_tracks"] = time.time() - step_start

            # Phase 2 STEP 3: Discover and validate artists
            step_start = time.time()
            await self._discover_and_validate_artists(state, intent_analysis, access_token)
            timing_metrics["discover_artists"] = time.time() - step_start

            # STEP 4: Get user's top tracks for additional seeds
            state.current_step = "gathering_seeds_fetching_top_tracks"
            await self._notify_progress(state)

            # Phase 1 Optimization: Pass user_id to enable caching
            step_start = time.time()
            top_tracks = await self.spotify_service.get_user_top_tracks(
                access_token=access_token,
                limit=20,
                time_range="medium_term",
                user_id=state.user_id
            )
            timing_metrics["fetch_top_tracks"] = time.time() - step_start

            # STEP 5: Get user's top artists for additional context
            state.current_step = "gathering_seeds_fetching_top_artists"
            await self._notify_progress(state)

            # Phase 1 Optimization: Pass user_id to enable caching
            step_start = time.time()
            top_artists = await self.spotify_service.get_user_top_artists(
                access_token=access_token,
                limit=15,
                time_range="medium_term",
                user_id=state.user_id
            )
            timing_metrics["fetch_top_artists"] = time.time() - step_start

            # STEP 6: Build optimized seed pool
            step_start = time.time()
            await self._build_seed_pool(state, top_tracks, top_artists, access_token)
            timing_metrics["build_seed_pool"] = time.time() - step_start

            # Update state
            state.current_step = "seeds_gathered"
            state.status = RecommendationStatus.GATHERING_SEEDS

            # Phase 1 Optimization: Log timing metrics
            total_time = time.time() - start_time
            timing_metrics["total"] = total_time

            logger.info(
                "Seed gathering completed (Phase 2)",
                total_time_seconds=f"{total_time:.2f}",
                search_user_tracks_seconds=f"{timing_metrics.get('search_user_tracks', 0):.2f}",
                select_anchors_seconds=f"{timing_metrics.get('select_anchor_tracks', 0):.2f}",
                discover_artists_seconds=f"{timing_metrics.get('discover_artists', 0):.2f}",
                fetch_top_tracks_seconds=f"{timing_metrics.get('fetch_top_tracks', 0):.2f}",
                fetch_top_artists_seconds=f"{timing_metrics.get('fetch_top_artists', 0):.2f}",
                build_seed_pool_seconds=f"{timing_metrics.get('build_seed_pool', 0):.2f}"
            )

            # Store timing metrics in state for analysis
            state.metadata["seed_gathering_timing"] = timing_metrics

            # Phase 4 Optimization: Save workflow artifacts for future reuse
            if not state.metadata.get("reused_artifacts"):
                workflow_artifacts = {
                    "artists": state.metadata.get("validated_artists", []),
                    "anchor_tracks": state.metadata.get("anchor_track_ids", []),
                    "audio_features": state.metadata.get("cached_audio_features", {}),
                    "computed_at": time.time()
                }

                await cache_manager.set_workflow_artifacts(
                    user_id=state.user_id,
                    mood_prompt=state.mood_prompt,
                    artifacts=workflow_artifacts
                )

                logger.info("Saved workflow artifacts for future reuse")

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
            state.metadata["user_mentioned_track_ids"] = []
            state.metadata["user_mentioned_tracks_full"] = []
            return

        state.current_step = "gathering_seeds_searching_user_tracks"
        await self._notify_progress(state)

        found_track_ids, found_tracks = await self.user_track_searcher.search_user_mentioned_tracks(
            user_mentioned_tracks, access_token
        )

        # Store in state metadata
        state.metadata["user_mentioned_track_ids"] = found_track_ids
        state.metadata["user_mentioned_tracks_full"] = found_tracks

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
            # Phase 4 Optimization: Try to reuse anchor tracks from workflow artifacts
            cached_anchor_ids = state.metadata.get("cached_anchor_tracks", [])
            if cached_anchor_ids:
                logger.info(f"Reusing {len(cached_anchor_ids)} anchor tracks from workflow artifacts")
                state.metadata["anchor_track_ids"] = cached_anchor_ids
                return

            # Phase 1 Optimization: Check cache for anchor tracks
            cached_anchors = await cache_manager.get_anchor_tracks(
                user_id=state.user_id,
                mood_prompt=state.mood_prompt
            )

            if cached_anchors is not None:
                logger.info(f"Cache hit for anchor tracks - using {len(cached_anchors)} cached anchors")
                anchor_ids = [track.get("id") for track in cached_anchors if track.get("id")]
                state.metadata["anchor_tracks"] = cached_anchors
                state.metadata["anchor_track_ids"] = anchor_ids
                return

            # Cache miss - compute anchor tracks
            # Prepare anchor selection parameters
            anchor_params = self._prepare_anchor_selection_params(state, intent_analysis)

            # Call anchor selection
            anchor_tracks, anchor_ids = await self.anchor_track_selector.select_anchor_tracks(**anchor_params)

            # Store results
            state.metadata["anchor_tracks"] = anchor_tracks
            state.metadata["anchor_track_ids"] = anchor_ids

            # Phase 1 Optimization: Cache the anchor tracks
            if anchor_tracks:
                await cache_manager.set_anchor_tracks(
                    user_id=state.user_id,
                    mood_prompt=state.mood_prompt,
                    anchor_tracks=anchor_tracks
                )
                logger.info(f"Cached {len(anchor_tracks)} anchor tracks")

            logger.info(f"✓ Selected {len(anchor_tracks)} anchor tracks")

        except Exception as e:
            logger.warning(f"Failed to select anchor tracks: {e}")
            state.metadata["anchor_tracks"] = []
            state.metadata["anchor_track_ids"] = []

    def _prepare_anchor_selection_params(
        self,
        state: AgentState,
        intent_analysis: dict
    ) -> dict:
        """Prepare parameters for anchor track selection.
        
        Args:
            state: Current agent state
            intent_analysis: Intent analysis data
            
        Returns:
            Dictionary of parameters for anchor selection
        """
        mood_analysis = state.mood_analysis or {}
        target_features = state.metadata.get("target_features", {})
        genre_keywords = mood_analysis.get("genre_keywords", [])
        artist_recommendations = mood_analysis.get("artist_recommendations", [])
        
        # Use intent analysis for stricter genre matching if available
        if intent_analysis.get("primary_genre"):
            genre_keywords = [intent_analysis["primary_genre"]] + genre_keywords

        # Extract user-mentioned artists from intent analysis (HIGHEST PRIORITY)
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])
        
        # Calculate appropriate anchor limit
        anchor_limit = self._calculate_anchor_limit(user_mentioned_artists)
        
        return {
            "genre_keywords": genre_keywords,
            "target_features": target_features,
            "access_token": state.metadata.get("spotify_access_token"),
            "mood_prompt": state.mood_prompt,
            "artist_recommendations": artist_recommendations,
            "mood_analysis": mood_analysis,
            "limit": anchor_limit,
            "user_mentioned_artists": user_mentioned_artists
        }

    def _calculate_anchor_limit(self, user_mentioned_artists: list) -> int:
        """Calculate appropriate anchor limit based on user-mentioned artists.
        
        Args:
            user_mentioned_artists: List of artists mentioned by user
            
        Returns:
            Appropriate anchor limit
        """
        base_limit = 5
        
        if not user_mentioned_artists:
            return base_limit
        
        # Guarantee at least 2 tracks per user-mentioned artist, plus some genre anchors
        min_needed = len(user_mentioned_artists) * 2  # 2 tracks per artist
        anchor_limit = max(base_limit, min_needed + 2)  # +2 for genre diversity
        
        logger.info(
            f"✓ Passing {len(user_mentioned_artists)} user-mentioned artists to anchor selection: "
            f"{user_mentioned_artists} (limit increased from {base_limit} to {anchor_limit})"
        )
        
        return anchor_limit

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
            # Phase 4 Optimization: Try to reuse artists from workflow artifacts
            cached_artists = state.metadata.get("cached_artists", [])
            if cached_artists:
                logger.info(f"Reusing {len(cached_artists)} artists from workflow artifacts")
                state.metadata["validated_artists"] = cached_artists
                return

            mood_analysis = state.mood_analysis or {}
            
            # Discover artists using mood analysis
            await self.artist_discovery.discover_mood_artists(state, mood_analysis)

            # Build artist lists from user-mentioned and anchor tracks
            user_mentioned_tracks = state.metadata.get("user_mentioned_tracks_full", [])
            user_mentioned_artists = [
                {
                    "id": track.get("artist_id"),
                    "name": track.get("artist"),
                    "popularity": track.get("popularity", 50),
                    "source": "user_mentioned"
                }
                for track in user_mentioned_tracks
                if track.get("artist_id")
            ]

            anchor_tracks = state.metadata.get("anchor_tracks", [])
            anchor_artists = [
                {
                    "id": track.get("artist_id"),
                    "name": track.get("artist"),
                    "popularity": track.get("popularity", 50),
                    "source": "anchor_track"
                }
                for track in anchor_tracks
                if track.get("artist_id")
            ]

            # Merge and deduplicate all artist sources using shared utility
            discovered_artists = state.metadata.get("discovered_artists", [])
            discovered_artists = ArtistDeduplicator.merge_and_deduplicate(
                discovered_artists,
                user_mentioned_artists,
                anchor_artists
            )
            state.metadata["discovered_artists"] = discovered_artists

            if user_mentioned_artists:
                logger.info(f"Added artists from {len(user_mentioned_tracks)} user-mentioned tracks")
            if anchor_artists:
                logger.info(f"Added artists from {len(anchor_tracks)} anchor tracks")
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
