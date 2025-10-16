"""Recommendation generation engine."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ...tools.reccobeat_service import RecoBeatService
from ...tools.spotify_service import SpotifyService
from ...states.agent_state import AgentState, TrackRecommendation
from ..utils import TokenService, TrackRecommendationFactory
from .audio_features import AudioFeaturesHandler
from .track_filter import TrackFilter
from .scoring_engine import ScoringEngine
from .strategies import ArtistDiscoveryStrategy, SeedBasedStrategy, FallbackStrategy

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Engine for generating track recommendations from various sources."""

    def __init__(self, reccobeat_service: RecoBeatService, spotify_service: SpotifyService):
        """Initialize the recommendation engine.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
        """
        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service

        # Initialize supporting components
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.track_filter = TrackFilter()
        self.scoring_engine = ScoringEngine()

        # Initialize recommendation strategies
        self.artist_strategy = ArtistDiscoveryStrategy(reccobeat_service, spotify_service)
        self.seed_strategy = SeedBasedStrategy(reccobeat_service)
        self.fallback_strategy = FallbackStrategy(reccobeat_service)

    async def _generate_mood_based_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations using strategy pattern for different sources.

        Target ratio: 95:5 (95% from artist discovery, 5% from seed-based recommendations).
        Artist discovery is overwhelmingly prioritized as RecoBeat recommendations tend to be lower quality.

        Args:
            state: Current agent state

        Returns:
            List of raw recommendations (mostly from artist discovery)
        """
        all_recommendations = []

        # Get target to calculate desired split
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)

        # Calculate target split: 95:5 ratio (95% artists, 5% seeds)
        target_artist_recs = int(target_count * 0.95)  # 95% from artists
        target_seed_recs = target_count - target_artist_recs  # 5% from seeds

        # Store targets in state for use by generation methods
        state.metadata["_temp_seed_target"] = target_seed_recs
        state.metadata["_temp_artist_target"] = target_artist_recs

        logger.info(
            f"Target generation split (95:5 ratio): {target_artist_recs} from artists, "
            f"{target_seed_recs} from seeds (total: {target_count})"
        )

        # Generate from discovered artists FIRST (aiming for 2/3 of target - higher priority)
        artist_recommendations = await self.artist_strategy.generate_recommendations(state, target_artist_recs)
        all_recommendations.extend(artist_recommendations)

        # Generate from seed tracks (aiming for 1/3 of target - supplement only)
        if state.seed_tracks:
            seed_recommendations = await self.seed_strategy.generate_recommendations(state, target_seed_recs)
            all_recommendations.extend(seed_recommendations)
        else:
            # Fallback strategy if no seeds available
            fallback_recommendations = await self.fallback_strategy.generate_recommendations(state, target_count)
            all_recommendations.extend(fallback_recommendations)

        # Clean up temp metadata
        state.metadata.pop("_temp_seed_target", None)
        state.metadata.pop("_temp_artist_target", None)

        logger.info(
            f"Generated {len(all_recommendations)} total recommendations "
            f"({len(artist_recommendations)} from artists [{target_artist_recs} target], "
            f"{len([r for r in all_recommendations if r.get('source') == 'reccobeat'])} from seeds/fallback [{target_seed_recs} target])"
        )

        return all_recommendations

