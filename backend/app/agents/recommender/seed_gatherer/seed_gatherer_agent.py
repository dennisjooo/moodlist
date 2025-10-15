"""Seed gatherer agent for collecting user preference data."""

import logging
from typing import Any, Dict, List, Optional

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, RecommendationStatus
from ...tools.spotify_service import SpotifyService
from .seed_selector import SeedSelector
from .audio_enricher import AudioEnricher
from .llm_seed_selector import LLMSeedSelector

logger = logging.getLogger(__name__)


class SeedGathererAgent(BaseAgent):
    """Agent for gathering seed tracks and artists from user data."""

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
            description="Gathers seed tracks and artists from user's Spotify listening history",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

        # Initialize component modules
        self.seed_selector = SeedSelector()
        self.audio_enricher = AudioEnricher(reccobeat_service)
        self.llm_seed_selector = LLMSeedSelector(llm)

    async def execute(self, state: AgentState) -> AgentState:
        """Execute seed gathering from user's Spotify data.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with seed data
        """
        try:
            logger.info(f"Gathering seeds for user {state.user_id}")

            # Check if we have Spotify access token
            if not hasattr(state, 'access_token') or not state.access_token:
                # Try to get from metadata or user record
                access_token = state.metadata.get("spotify_access_token")
                if not access_token:
                    raise ValueError("No Spotify access token available for seed gathering")

            # Get user's top tracks for seeds
            top_tracks = await self.spotify_service.get_user_top_tracks(
                access_token=access_token,
                limit=20,
                time_range="medium_term"
            )

            # Get user's top artists for additional context
            top_artists = await self.spotify_service.get_user_top_artists(
                access_token=access_token,
                limit=15,
                time_range="medium_term"
            )

            # Process and select seed tracks
            # Get target features and weights from metadata where mood analyzer stored them
            target_features = state.metadata.get("target_features", {})
            feature_weights = state.metadata.get("feature_weights", {})

            # Enhance target_features with weights for more sophisticated matching
            if feature_weights:
                target_features["_weights"] = feature_weights

            # Fetch audio features for top tracks if RecoBeat service available
            top_tracks = await self.audio_enricher.enrich_tracks_with_features(top_tracks)

            # Select seed tracks using audio feature scoring
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

            # Store user's top track IDs in state for reference (full list, not just seeds)
            user_track_ids = [track["id"] for track in top_tracks if track.get("id")]
            state.user_top_tracks = user_track_ids

            # Extract artist IDs for context
            artist_ids = [artist["id"] for artist in top_artists if artist.get("id")]
            state.user_top_artists = artist_ids

            # Update state
            state.current_step = "seeds_gathered"
            state.status = RecommendationStatus.GATHERING_SEEDS

            # Store additional metadata
            state.metadata["seed_track_count"] = len(final_seeds)
            state.metadata["user_track_count"] = len(user_track_ids)
            state.metadata["top_artist_count"] = len(artist_ids)
            state.metadata["seed_source"] = "spotify_top_tracks_ai_selected"

            logger.info(
                f"Gathered {len(final_seeds)} seed tracks from {len(user_track_ids)} user top tracks "
                f"and {len(artist_ids)} artists"
            )

        except Exception as e:
            logger.error(f"Error in seed gathering: {str(e)}", exc_info=True)
            state.set_error(f"Seed gathering failed: {str(e)}")

        return state