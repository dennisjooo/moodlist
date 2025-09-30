"""Seed gatherer agent for collecting user preference data."""

import logging
from typing import Any, Dict, List, Optional

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.spotify_service import SpotifyService


logger = logging.getLogger(__name__)


class SeedGathererAgent(BaseAgent):
    """Agent for gathering seed tracks and artists from user data."""

    def __init__(
        self,
        spotify_service: SpotifyService,
        verbose: bool = False
    ):
        """Initialize the seed gatherer agent.

        Args:
            spotify_service: Service for Spotify API operations
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="seed_gatherer",
            description="Gathers seed tracks and artists from user's Spotify listening history",
            verbose=verbose
        )

        self.spotify_service = spotify_service

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
            seed_tracks = self._select_seed_tracks(top_tracks, state.mood_analysis)
            state.seed_tracks = seed_tracks

            # Extract artist IDs for context
            artist_ids = [artist["id"] for artist in top_artists if artist.get("id")]
            state.user_top_artists = artist_ids

            # Update state
            state.current_step = "seeds_gathered"
            state.status = RecommendationStatus.GATHERING_SEEDS

            # Store additional metadata
            state.metadata["seed_track_count"] = len(seed_tracks)
            state.metadata["top_artist_count"] = len(artist_ids)
            state.metadata["seed_source"] = "spotify_top_tracks"

            logger.info(f"Gathered {len(seed_tracks)} seed tracks and {len(artist_ids)} artists")

        except Exception as e:
            logger.error(f"Error in seed gathering: {str(e)}", exc_info=True)
            state.set_error(f"Seed gathering failed: {str(e)}")

        return state

    def _select_seed_tracks(
        self,
        top_tracks: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Select the best tracks to use as seeds.

        Args:
            top_tracks: User's top tracks from Spotify
            mood_analysis: Optional mood analysis for filtering

        Returns:
            List of selected track IDs
        """
        if not top_tracks:
            logger.warning("No top tracks available for seed selection")
            return []

        # Filter out tracks without IDs
        valid_tracks = [track for track in top_tracks if track.get("id")]

        if not valid_tracks:
            logger.warning("No valid track IDs found in top tracks")
            return []

        # Select top tracks based on popularity and relevance
        selected_tracks = []

        # Prioritize tracks that match mood if analysis available
        if mood_analysis and mood_analysis.get("target_features"):
            target_features = mood_analysis["target_features"]

            # Score tracks based on how well they might match the mood
            scored_tracks = []
            for track in valid_tracks[:30]:  # Consider top 30 tracks
                score = self._calculate_mood_match_score(track, target_features)
                scored_tracks.append((track, score))

            # Sort by score and take top tracks
            scored_tracks.sort(key=lambda x: x[1], reverse=True)
            selected_tracks = [track["id"] for track, _ in scored_tracks[:10]]

        else:
            # Default selection: take top tracks by popularity
            # Sort by popularity (descending)
            sorted_tracks = sorted(
                valid_tracks,
                key=lambda x: x.get("popularity", 0),
                reverse=True
            )
            selected_tracks = [track["id"] for track in sorted_tracks[:10]]

        logger.info(f"Selected {len(selected_tracks)} seed tracks from {len(valid_tracks)} available tracks")

        return selected_tracks

    def _calculate_mood_match_score(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track matches target mood features.

        Args:
            track: Track information
            target_features: Target audio features from mood analysis

        Returns:
            Match score (0-1, higher is better)
        """
        score = 0.5  # Base score

        track_popularity = track.get("popularity", 50)

        # Popularity factor (normalize to 0-1)
        popularity_factor = track_popularity / 100.0

        # Weight popularity moderately
        score = 0.3 + (0.7 * popularity_factor)

        # If we have specific feature targets, we could enhance this
        # For now, we'll rely on popularity as a proxy for quality

        return min(score, 1.0)  # Cap at 1.0

    def _get_negative_seeds(
        self,
        top_tracks: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[str]:
        """Get tracks to avoid in recommendations.

        Args:
            top_tracks: User's top tracks
            mood_analysis: Optional mood analysis
            limit: Maximum number of negative seeds

        Returns:
            List of track IDs to avoid
        """
        # For now, we'll use least popular tracks as negative examples
        # This is a simple heuristic - could be enhanced

        valid_tracks = [track for track in top_tracks if track.get("id")]

        # Sort by popularity (ascending) - least popular first
        sorted_tracks = sorted(
            valid_tracks,
            key=lambda x: x.get("popularity", 50)
        )

        # Take least popular tracks as negative examples
        negative_seeds = [track["id"] for track in sorted_tracks[:limit]]

        logger.info(f"Selected {len(negative_seeds)} negative seed tracks")

        return negative_seeds