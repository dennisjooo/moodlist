"""Recommendation generation engine."""

import asyncio
import structlog
from typing import Any, Dict, List

from ....tools.reccobeat_service import RecoBeatService
from ....tools.spotify_service import SpotifyService
from ....states.agent_state import AgentState
from ..generators.seed_based import SeedBasedGenerator
from ..generators.artist_based import ArtistBasedGenerator
from ..handlers.anchor_track import AnchorTrackHandler

logger = structlog.get_logger(__name__)


class RecommendationEngine:
    """Engine for generating track recommendations from various sources.
    
    Uses specialized generators for better separation of concerns.
    """

    def __init__(self, reccobeat_service: RecoBeatService, spotify_service: SpotifyService):
        """Initialize the recommendation engine.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
        """
        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service

        # Initialize specialized generators
        self.seed_generator = SeedBasedGenerator(reccobeat_service)
        self.artist_generator = ArtistBasedGenerator(spotify_service, reccobeat_service)
        self.anchor_handler = AnchorTrackHandler()

    async def _generate_mood_based_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations based on mood analysis, seeds, and discovered artists.

        Recommendation mix with User Anchor Strategy:
        - 40% User Anchor Strategy (if user mentioned tracks/artists)
        - 40% Artist Discovery
        - 15% Seed-Based
        - 5%  RecoBeat fallback

        Executes strategies in parallel for improved performance.

        Args:
            state: Current agent state

        Returns:
            List of raw recommendations
        """
        all_recommendations = []

        # Calculate target splits based on user mentions
        self._calculate_target_splits(state)

        # Execute all three strategies in parallel for maximum throughput
        logger.info("Executing recommendation strategies in parallel")

        user_anchor_recs, artist_recs, seed_recs = await asyncio.gather(
            self._generate_from_user_anchors(state),
            self.artist_generator.generate_recommendations(state),
            self.seed_generator.generate_recommendations(state),
            return_exceptions=True  # Continue if one strategy fails
        )

        # Handle exceptions from parallel execution
        if isinstance(user_anchor_recs, Exception):
            logger.error(f"User anchor strategy failed: {user_anchor_recs}")
            user_anchor_recs = []
        if isinstance(artist_recs, Exception):
            logger.error(f"Artist strategy failed: {artist_recs}")
            artist_recs = []
        if isinstance(seed_recs, Exception):
            logger.error(f"Seed strategy failed: {seed_recs}")
            seed_recs = []

        # Combine all recommendations
        all_recommendations.extend(user_anchor_recs)
        all_recommendations.extend(artist_recs)
        all_recommendations.extend(seed_recs)

        # Note: Anchor tracks are already added to state at the start of recommendation generation
        # We don't include them here again to avoid duplicates
        # all_recommendations = self.anchor_handler.include_anchor_tracks(state, all_recommendations)

        # Clean up temp metadata
        state.metadata.pop("_temp_seed_target", None)
        state.metadata.pop("_temp_artist_target", None)
        state.metadata.pop("_temp_user_anchor_target", None)

        logger.info(
            f"Generated {len(all_recommendations)} total recommendations in parallel "
            f"({len(user_anchor_recs)} user anchor, {len(artist_recs)} artists, {len(seed_recs)} seeds)"
        )

        return all_recommendations

    def _calculate_target_splits(self, state: AgentState) -> None:
        """Calculate target recommendation splits based on user mentions.

        Args:
            state: Current agent state
        """
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)

        # Check if user mentioned tracks/artists
        user_mentioned_track_ids = state.metadata.get("user_mentioned_track_ids", [])
        intent_analysis = state.metadata.get("intent_analysis", {})
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])
        has_user_mentions = bool(user_mentioned_track_ids or user_mentioned_artists)

        if has_user_mentions:
            # WITH user mentions: 40% user anchor, 55% artists, 0% seeds (Recobeat overflow only)
            target_user_anchor_recs = int(target_count * 0.40)
            target_artist_recs = int(target_count * 0.55)
            target_seed_recs = 0

            logger.info(
                f"Split WITH user mentions: {target_user_anchor_recs} user anchor, "
                f"{target_artist_recs} artists, {target_seed_recs} seeds (total: {target_count})"
            )
        else:
            # WITHOUT user mentions: 90% artists, 0% seeds (Recobeat overflow only)
            target_user_anchor_recs = 0
            target_artist_recs = int(target_count * 0.90)
            target_seed_recs = 0

            logger.info(
                f"Split WITHOUT user mentions: {target_artist_recs} artists, "
                f"{target_seed_recs} seeds (total: {target_count})"
            )

        # Store targets in state for generators
        state.metadata["_temp_seed_target"] = target_seed_recs
        state.metadata["_temp_artist_target"] = target_artist_recs
        state.metadata["_temp_user_anchor_target"] = target_user_anchor_recs

    async def _generate_from_user_anchors(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations using the user anchor strategy.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from user anchor strategy
        """
        from ..strategies import UserAnchorStrategy

        target_count = state.metadata.get("_temp_user_anchor_target", 0)
        if target_count == 0:
            return []

        try:
            # Initialize user anchor strategy
            user_anchor_strategy = UserAnchorStrategy(
                spotify_service=self.spotify_service,
                reccobeat_service=self.reccobeat_service
            )

            # Generate recommendations
            recommendations = await user_anchor_strategy.generate_recommendations(state, target_count)

            logger.info(f"User anchor strategy generated {len(recommendations)} recommendations")

            return recommendations

        except Exception as e:
            logger.error(f"Error in user anchor strategy: {e}", exc_info=True)
            return []

    async def _generate_fallback_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when no seeds are available.

        Args:
            state: Current agent state

        Returns:
            List of fallback recommendations
        """
        logger.info("Generating fallback recommendations without seeds")

        # Use mood-based search with artist keywords
        if state.mood_analysis:
            keywords = state.mood_analysis.get("keywords") or state.mood_analysis.get("search_keywords")

            if keywords:
                # Use top 3 keywords
                keywords_to_use = keywords[:3] if isinstance(keywords, list) else [keywords]

                # Search for artists matching mood keywords
                matching_artists = await self.reccobeat_service.search_artists_by_mood(
                    keywords_to_use,
                    limit=5
                )

                if matching_artists:
                    # Use found artists as seeds for recommendations
                    artist_ids = [artist["id"] for artist in matching_artists if artist.get("id")]

                    if artist_ids:
                        # Deduplicate artist IDs
                        unique_artist_ids = list(dict.fromkeys(artist_ids[:3]))
                        fallback_recommendations = await self.reccobeat_service.get_track_recommendations(
                            seeds=unique_artist_ids,
                            size=20
                        )

                        logger.info(
                            f"Generated {len(fallback_recommendations)} fallback recommendations "
                            f"using {len(artist_ids)} artists"
                        )
                        return fallback_recommendations

        # If all else fails, return empty list
        logger.warning("Could not generate fallback recommendations")
        return []
