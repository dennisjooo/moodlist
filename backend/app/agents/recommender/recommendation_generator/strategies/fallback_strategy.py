"""Fallback strategy for generating recommendations when no seeds are available."""

import structlog
from typing import Any, Dict, List

from ....tools.reccobeat_service import RecoBeatService
from ....states.agent_state import AgentState
from .base_strategy import RecommendationStrategy

logger = structlog.get_logger(__name__)


class FallbackStrategy(RecommendationStrategy):
    """Fallback strategy for generating recommendations when no seeds are available."""

    def __init__(self, reccobeat_service: RecoBeatService):
        """Initialize the fallback strategy.

        Args:
            reccobeat_service: Service for RecoBeat API operations
        """
        super().__init__("fallback")
        self.reccobeat_service = reccobeat_service

    async def generate_recommendations(
        self, state: AgentState, target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when no seeds are available.

        Args:
            state: Current agent state
            target_count: Target number of recommendations to generate

        Returns:
            List of recommendation data dictionaries
        """
        logger.info("Generating fallback recommendations without seeds")

        # Use mood-based search with artist keywords
        # Support both old format (search_keywords) and new format (keywords)
        if state.mood_analysis:
            keywords = state.mood_analysis.get("keywords") or state.mood_analysis.get(
                "search_keywords"
            )

            if keywords:
                # Use top 3 keywords
                keywords_to_use = (
                    keywords[:3] if isinstance(keywords, list) else [keywords]
                )

                # Search for artists matching mood keywords
                matching_artists = await self.reccobeat_service.search_artists_by_mood(
                    keywords_to_use, limit=5
                )

                if matching_artists:
                    # Use found artists as seeds for recommendations
                    artist_ids = [
                        artist["id"] for artist in matching_artists if artist.get("id")
                    ]

                    if artist_ids:
                        # Deduplicate artist IDs
                        unique_artist_ids = list(dict.fromkeys(artist_ids[:3]))
                        fallback_recommendations = (
                            await self.reccobeat_service.get_track_recommendations(
                                seeds=unique_artist_ids,
                                size=min(target_count, 20),
                                # NO audio feature params - keep it simple
                            )
                        )

                        logger.info(
                            f"Generated {len(fallback_recommendations)} fallback recommendations using {len(artist_ids)} artists"
                        )
                        return fallback_recommendations

        # If all else fails, return empty list
        logger.warning("Could not generate fallback recommendations")
        return []
