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
            # Get target features and weights from metadata where mood analyzer stored them
            target_features = state.metadata.get("target_features", {})
            feature_weights = state.metadata.get("feature_weights", {})

            # Enhance target_features with weights for more sophisticated matching
            if feature_weights:
                target_features["_weights"] = feature_weights

            seed_tracks = self._select_seed_tracks(top_tracks, target_features)
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
        target_features: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Select the best tracks to use as seeds.

        Args:
            top_tracks: User's top tracks from Spotify
            mood_analysis: Optional mood analysis for filtering
            target_features: Target audio features from mood analysis

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

        # Prioritize tracks that match mood if target features available
        if target_features:
            # Score tracks based on how well they match the target features
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
        """Calculate how well a track matches target mood features using all available audio features and weights.

        Args:
            track: Track information from Spotify
            target_features: Target audio features from mood analysis (may include _weights)

        Returns:
            Match score (0-1, higher is better)
        """
        if not target_features:
            # Fallback to popularity if no target features
            return track.get("popularity", 50) / 100.0

        # Extract feature weights if provided, otherwise use defaults
        feature_weights = target_features.get("_weights", self._get_default_feature_weights())

        total_score = 0.0
        total_weight = 0.0

        # Calculate match score for each available feature
        for feature, target_value in target_features.items():
            if feature == "_weights" or feature not in feature_weights:
                continue

            weight = feature_weights.get(feature, 0.1)  # Default weight if not specified
            track_value = self._get_track_feature_value(track, feature)

            if track_value is not None:
                # Calculate similarity score (0-1) for this feature
                feature_score = self._calculate_feature_similarity(
                    track_value, target_value, feature
                )

                total_score += feature_score * weight
                total_weight += weight

        # Normalize by total weight
        if total_weight == 0:
            return track.get("popularity", 50) / 100.0

        final_score = total_score / total_weight

        # Boost score slightly for popular tracks (they're likely to be good seeds)
        popularity_boost = min(track.get("popularity", 50) / 1000.0, 0.1)

        return min(final_score + popularity_boost, 1.0)

    def _get_default_feature_weights(self) -> Dict[str, float]:
        """Get default feature weights when none are provided by mood analysis."""
        return {
            "energy": 0.15,
            "valence": 0.15,
            "danceability": 0.12,
            "acousticness": 0.12,
            "instrumentalness": 0.10,
            "tempo": 0.08,
            "mode": 0.08,
            "loudness": 0.06,
            "speechiness": 0.05,
            "liveness": 0.05,
            "key": 0.03,
            "popularity": 0.01
        }

    def _get_track_feature_value(self, track: Dict[str, Any], feature: str) -> Optional[float]:
        """Extract feature value from Spotify track data.

        Args:
            track: Spotify track information
            feature: Feature name to extract

        Returns:
            Feature value or None if not available
        """
        # Map feature names to Spotify track structure
        feature_mapping = {
            "energy": track.get("energy"),
            "valence": track.get("valence"),
            "danceability": track.get("danceability"),
            "acousticness": track.get("acousticness"),
            "instrumentalness": track.get("instrumentalness"),
            "tempo": track.get("tempo"),
            "mode": track.get("mode"),
            "loudness": track.get("loudness"),
            "speechiness": track.get("speechiness"),
            "liveness": track.get("liveness"),
            "key": track.get("key"),
            "popularity": track.get("popularity")
        }

        return feature_mapping.get(feature)

    def _calculate_feature_similarity(
        self,
        track_value: float,
        target_value: float,
        feature: str
    ) -> float:
        """Calculate similarity between track feature and target feature.

        Args:
            track_value: Actual feature value from track
            target_value: Target feature value from mood analysis
            feature: Name of the feature being compared

        Returns:
            Similarity score (0-1, higher is better)
        """
        if feature in ["tempo", "loudness", "key", "popularity"]:
            # For continuous numeric features, use distance-based similarity
            if feature == "tempo":
                # Tempo similarity - closer BPMs are more similar
                max_diff = 60  # BPM
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "loudness":
                # Loudness similarity - closer dB values are more similar
                max_diff = 30  # dB
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "key":
                # Key similarity - exact match or adjacent keys
                if track_value == target_value:
                    return 1.0
                elif abs(track_value - target_value) == 1:
                    return 0.8  # Adjacent keys are somewhat similar
                else:
                    return 0.3  # Other keys are less similar
            elif feature == "popularity":
                # Popularity similarity - lower popularity for indie moods
                max_diff = 100
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))

        # For normalized features (0-1), use direct distance
        diff = abs(track_value - target_value)
        return max(0, 1 - diff)

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