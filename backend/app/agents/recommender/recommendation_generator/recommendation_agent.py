"""Main recommendation generator agent."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import httpx

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
from ...tools.reccobeat_service import RecoBeatService
from ...tools.spotify_service import SpotifyService
from .token_manager import TokenManager
from .recommendation_engine import RecommendationEngine
from .audio_features import AudioFeaturesHandler
from .track_filter import TrackFilter
from .scoring_engine import ScoringEngine
from .diversity_manager import DiversityManager


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
            
            # Apply ratio limits and get final recommendations
            final_recommendations = self._apply_ratio_limits(processed_recommendations, state)

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
        # Filter and rank recommendations
        filtered_recommendations = self.track_filter._filter_and_rank_recommendations(
            recommendations, state.mood_analysis
        )

        # Ensure diversity in recommendations
        return self.diversity_manager._ensure_diversity(filtered_recommendations)

    def _apply_ratio_limits(
        self,
        recommendations: List[TrackRecommendation],
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Apply 95:5 ratio limits between artist discovery and RecoBeat tracks.

        Args:
            recommendations: Processed recommendations
            state: Current agent state

        Returns:
            Final recommendations with ratio limits applied
        """
        # Get playlist target to determine max recommendations
        playlist_target = state.metadata.get("playlist_target", {})
        max_recommendations = playlist_target.get("max_count", self.max_recommendations)

        # ENFORCE 98:2 ratio: separate artist discovery, anchor, and RecoBeat tracks
        artist_recs = [r for r in recommendations if r.source == "artist_discovery"]
        anchor_recs = [r for r in recommendations if r.source == "anchor_track"]
        reccobeat_recs = [r for r in recommendations if r.source == "reccobeat"]

        # Calculate strict caps based on 98:2 ratio (anchor tracks don't count toward ratio)
        max_artist = int(max_recommendations * 0.98)  # 98% (increased from 95%)
        max_reccobeat = max(1, max_recommendations - max_artist)  # Minimum 1 for edge cases

        # CRITICAL: User-mentioned anchors don't count toward the anchor limit
        # Separate user-mentioned from other anchors
        user_mentioned_anchors = [r for r in anchor_recs if r.user_mentioned]
        other_anchors = [r for r in anchor_recs if not r.user_mentioned]
        
        # Cap non-user-mentioned anchors to 5, but ALWAYS include all user-mentioned
        capped_other_anchors = other_anchors[:5]
        capped_anchor = user_mentioned_anchors + capped_other_anchors
        
        logger.info(
            f"Anchor breakdown: {len(user_mentioned_anchors)} user-mentioned (unlimited), "
            f"{len(capped_other_anchors)} other anchors (capped at 5)"
        )
        
        # Adjust caps to account for anchor tracks
        remaining_slots = max_recommendations - len(capped_anchor)
        max_artist = int(remaining_slots * 0.98)
        max_reccobeat = max(1, remaining_slots - max_artist)

        # Take top tracks from each source up to their caps
        capped_artist = artist_recs[:max_artist]
        capped_reccobeat = reccobeat_recs[:max_reccobeat]

        logger.info(
            f"Enforcing 98:2 ratio: {len(capped_anchor)} anchor + {len(capped_artist)} artist tracks (cap: {max_artist}), "
            f"{len(capped_reccobeat)} RecoBeat tracks (cap: {max_reccobeat}) - RecoBeat minimal fallback only"
        )

        # CRITICAL: Sort each group independently but maintain priority order
        # Anchor tracks (especially user-mentioned) MUST stay at the top
        capped_anchor.sort(key=lambda x: x.confidence_score, reverse=True)
        capped_artist.sort(key=lambda x: x.confidence_score, reverse=True)
        capped_reccobeat.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Combine with anchors first (NEVER re-sort after this!)
        final_recommendations = capped_anchor + capped_artist + capped_reccobeat

        return final_recommendations

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
            # Check track ID
            if rec.track_id in seen_track_ids:
                logger.debug(f"Skipping duplicate track ID: {rec.track_name} by {', '.join(rec.artists)}")
                continue

            # Check normalized track name (case-insensitive, remove feat/featuring variations)
            normalized_name = rec.track_name.lower()
            # Remove common variations that create duplicates
            for variant in [" (radio edit)", " - radio edit", " (feat.", " (featuring ", " - feat.", " - featuring "]:
                if variant in normalized_name:
                    normalized_name = normalized_name.split(variant)[0]
            normalized_name = normalized_name.strip()

            if normalized_name in seen_normalized_names:
                logger.debug(f"Skipping duplicate track name: {rec.track_name} by {', '.join(rec.artists)}")
                continue

            # Check Spotify URI
            if rec.spotify_uri and rec.spotify_uri in seen_spotify_uris:
                logger.debug(f"Skipping duplicate Spotify URI: {rec.track_name} by {', '.join(rec.artists)}")
                continue

            # No duplicates found, add the track
            state.add_recommendation(rec)
            seen_track_ids.add(rec.track_id)
            seen_normalized_names.add(normalized_name)
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
