"""Seed selector for choosing the best tracks as seeds."""

import structlog
from typing import Any, Dict, List, Optional

from .feature_matcher import FeatureMatcher

logger = structlog.get_logger(__name__)


class SeedSelector:
    """Handles seed track selection and negative seed identification."""

    def __init__(self):
        """Initialize the seed selector."""
        self.feature_matcher = FeatureMatcher()

    def select_seed_tracks(
        self,
        top_tracks: List[Dict[str, Any]],
        target_features: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Select the best tracks to use as seeds with scoring.

        Args:
            top_tracks: User's top tracks from Spotify
            target_features: Target audio features from mood analysis

        Returns:
            List of selected track IDs (ordered by score)
        """
        if not top_tracks:
            logger.warning("No top tracks available for seed selection")
            return []

        # Filter out tracks without IDs
        valid_tracks = [track for track in top_tracks if track.get("id")]

        if not valid_tracks:
            logger.warning("No valid track IDs found in top tracks")
            return []

        # Prioritize tracks that match mood if target features available
        if target_features:
            # Score tracks based on how well they match the target features
            scored_tracks = []
            for track in valid_tracks[:30]:  # Consider top 30 tracks
                score = self.feature_matcher.calculate_mood_match_score(track, target_features)
                scored_tracks.append((track["id"], score, track))

            # Sort by score and return track IDs
            scored_tracks.sort(key=lambda x: x[1], reverse=True)
            selected_tracks = [track_id for track_id, _, _ in scored_tracks]

            logger.info(f"Scored {len(scored_tracks)} tracks, top score: {scored_tracks[0][1]:.2f}")
            return selected_tracks
        else:
            # Default selection: take top tracks by popularity
            sorted_tracks = sorted(
                valid_tracks,
                key=lambda x: x.get("popularity", 0),
                reverse=True
            )
            selected_tracks = [track["id"] for track in sorted_tracks]

        logger.info(f"Selected {len(selected_tracks)} seed track candidates")
        return selected_tracks

    def get_negative_seeds(
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