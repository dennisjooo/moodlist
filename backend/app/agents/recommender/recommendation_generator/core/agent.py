"""Main recommendation generator agent."""

import structlog
from typing import Any, Dict, List

from ....core.base_agent import BaseAgent
from ....states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
from ....tools.reccobeat_service import RecoBeatService
from ....tools.spotify_service import SpotifyService
from ...orchestrator.recommendation_processor import RecommendationProcessor
from ..handlers.token import TokenManager
from ..handlers.audio_features import AudioFeaturesHandler
from ..handlers.track_filter import TrackFilter
from ..handlers.scoring import ScoringEngine
from ..handlers.diversity import DiversityManager
from .engine import RecommendationEngine


logger = structlog.get_logger(__name__)


class RecommendationGeneratorAgent(BaseAgent):
    """Agent for generating mood-based track recommendations."""

    def __init__(
        self,
        reccobeat_service: RecoBeatService,
        spotify_service: SpotifyService,
        max_recommendations: int = 30,
        diversity_factor: float = 0.7,
        verbose: bool = False
    ):
        """Initialize the recommendation generator agent.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
            max_recommendations: Maximum number of recommendations to generate
            diversity_factor: Factor for ensuring diversity in recommendations (0-1)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="recommendation_generator",
            description="Generates sophisticated mood-based track recommendations using RecoBeat API",
            verbose=verbose
        )

        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service
        self.max_recommendations = max_recommendations
        self.diversity_factor = diversity_factor

        # Initialize component classes
        self.token_manager = TokenManager()
        self.recommendation_engine = RecommendationEngine(reccobeat_service, spotify_service)
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.track_filter = TrackFilter()
        self.scoring_engine = ScoringEngine()
        self.diversity_manager = DiversityManager()
        self.recommendation_processor = RecommendationProcessor()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute recommendation generation.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with recommendations
        """
        try:
            logger.info(f"Generating recommendations for mood: {state.mood_prompt}")

            # Update: Fetching recommendations
            state.current_step = "generating_recommendations_fetching"
            await self._notify_progress(state)
            
            # Get raw recommendations
            recommendations = await self._get_recommendations(state)

            # Update: Processing and ranking
            state.current_step = "generating_recommendations_processing"
            await self._notify_progress(state)
            
            # Process recommendations (filter, rank, diversify)
            processed_recommendations = await self._process_recommendations(recommendations, state)

            # Update: Applying diversity
            state.current_step = "generating_recommendations_diversifying"
            await self._notify_progress(state)

            # Apply ratio limits and get final recommendations using the shared processor
            # Use 98:2 ratio (0.98 for artist discovery) to minimize RecoBeat fallback
            max_recommendations = self._get_max_recommendations(state)
            final_recommendations = self.recommendation_processor.enforce_source_ratio(
                recommendations=processed_recommendations,
                max_count=max_recommendations,
                artist_ratio=0.98
            )

            # Deduplicate and add to state
            self._deduplicate_and_add_recommendations(final_recommendations, state)

            # Update state with final metadata
            self._update_state_metadata(state, processed_recommendations)

            logger.info(f"Generated {len(state.recommendations)} final recommendations")

        except Exception as e:
            logger.error(f"Error in recommendation generation: {str(e)}", exc_info=True)
            state.set_error(f"Recommendation generation failed: {str(e)}")

        return state

    async def _get_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Get raw recommendations based on available seeds.

        Args:
            state: Current agent state

        Returns:
            Raw recommendations list
        """
        if not state.seed_tracks:
            logger.warning("No seed tracks available for recommendations")
            return await self.recommendation_engine._generate_fallback_recommendations(state)
        else:
            return await self.recommendation_engine._generate_mood_based_recommendations(state)

    async def _process_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Process recommendations through filtering, ranking, and diversity steps.

        Args:
            recommendations: Raw recommendations
            state: Current agent state

        Returns:
            Processed TrackRecommendation objects
        """
        # Filter and rank recommendations (with negative seeds exclusion)
        filtered_recommendations = self.track_filter._filter_and_rank_recommendations(
            recommendations, state.mood_analysis, negative_seeds=state.negative_seeds
        )

        # Ensure diversity in recommendations
        return self.diversity_manager._ensure_diversity(filtered_recommendations)


    def _get_max_recommendations(self, state: AgentState) -> int:
        """Get maximum recommendations from playlist target.

        Args:
            state: Current agent state

        Returns:
            Maximum number of recommendations
        """
        playlist_target = state.metadata.get("playlist_target", {})
        return playlist_target.get("max_count", self.max_recommendations)

    def _deduplicate_and_add_recommendations(
        self,
        recommendations: List[TrackRecommendation],
        state: AgentState
    ) -> None:
        """Deduplicate recommendations and add them to state.

        Args:
            recommendations: Final recommendations to add
            state: Current agent state
        """
        seen_track_ids = set()
        seen_normalized_names = set()
        seen_spotify_uris = set()

        for rec in recommendations:
            # Check for duplicates
            if self._is_duplicate(rec, seen_track_ids, seen_normalized_names, seen_spotify_uris):
                continue

            # No duplicates found, add the track
            state.add_recommendation(rec)
            self._mark_as_seen(rec, seen_track_ids, seen_normalized_names, seen_spotify_uris)

    def _is_duplicate(
        self,
        rec: TrackRecommendation,
        seen_track_ids: set,
        seen_normalized_names: set,
        seen_spotify_uris: set
    ) -> bool:
        """Check if recommendation is a duplicate.

        Args:
            rec: Track recommendation to check
            seen_track_ids: Set of seen track IDs
            seen_normalized_names: Set of seen normalized track names
            seen_spotify_uris: Set of seen Spotify URIs

        Returns:
            True if duplicate, False otherwise
        """
        # Check track ID
        if rec.track_id in seen_track_ids:
            logger.debug(f"Skipping duplicate track ID: {rec.track_name} by {', '.join(rec.artists)}")
            return True

        # Check normalized track name
        normalized_name = self._normalize_track_name(rec.track_name)
        if normalized_name in seen_normalized_names:
            logger.debug(f"Skipping duplicate track name: {rec.track_name} by {', '.join(rec.artists)}")
            return True

        # Check Spotify URI
        if rec.spotify_uri and rec.spotify_uri in seen_spotify_uris:
            logger.debug(f"Skipping duplicate Spotify URI: {rec.track_name} by {', '.join(rec.artists)}")
            return True

        return False

    def _normalize_track_name(self, track_name: str) -> str:
        """Normalize track name for duplicate detection.

        Args:
            track_name: Original track name

        Returns:
            Normalized track name
        """
        normalized_name = track_name.lower()
        
        # Remove common variations that create duplicates
        variants = [
            " (radio edit)", " - radio edit", 
            " (feat.", " (featuring ", 
            " - feat.", " - featuring "
        ]
        
        for variant in variants:
            if variant in normalized_name:
                normalized_name = normalized_name.split(variant)[0]
        
        return normalized_name.strip()

    def _mark_as_seen(
        self,
        rec: TrackRecommendation,
        seen_track_ids: set,
        seen_normalized_names: set,
        seen_spotify_uris: set
    ) -> None:
        """Mark recommendation as seen in tracking sets.

        Args:
            rec: Track recommendation
            seen_track_ids: Set of seen track IDs
            seen_normalized_names: Set of seen normalized track names
            seen_spotify_uris: Set of seen Spotify URIs
        """
        seen_track_ids.add(rec.track_id)
        seen_normalized_names.add(self._normalize_track_name(rec.track_name))
        if rec.spotify_uri:
            seen_spotify_uris.add(rec.spotify_uri)

    def _update_state_metadata(
        self,
        state: AgentState,
        processed_recommendations: List[TrackRecommendation]
    ) -> None:
        """Update state with final metadata.

        Args:
            state: Current agent state
            processed_recommendations: The processed recommendations before ratio limits
        """
        state.current_step = "recommendations_generated"
        state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS

        # Store metadata
        state.metadata["total_recommendations_generated"] = len(processed_recommendations)
        state.metadata["final_recommendation_count"] = len(state.recommendations)
        state.metadata["recommendation_strategy"] = "mood_based_with_seeds"
