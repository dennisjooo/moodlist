"""Remix mode handling and optimizations.

This module handles:
- Detecting and setting up remix mode
- Normalizing remix tracks to anchor format
- Optimizing mood analysis for remix mode
- Managing remix-specific optimizations
"""

import structlog

from ...states.agent_state import AgentState


logger = structlog.get_logger(__name__)


class RemixHandler:
    """Handles remix-specific logic and optimizations."""

    def setup_remix_mode(self, state: AgentState) -> tuple[bool, list]:
        """Check for remix mode and set up state accordingly.

        Args:
            state: Current agent state

        Returns:
            Tuple of (is_remix, remix_tracks)
        """
        remix_tracks = state.metadata.get("remix_playlist_tracks")
        is_remix = bool(remix_tracks)

        if is_remix:
            state.metadata["is_remix"] = True
            logger.info("Remix mode detected: optimizing seed gathering steps")

        return is_remix, remix_tracks

    def normalize_remix_anchors(self, anchor_candidates: list) -> list:
        """Normalize remix tracks to match expected anchor format.

        Args:
            anchor_candidates: Raw remix tracks to normalize

        Returns:
            List of normalized anchor tracks
        """
        normalized_anchors = []
        for track in anchor_candidates:
            # Handle different artist formats (list of strings vs list of dicts)
            raw_artists = track.get("artists", [])
            formatted_artists = []

            for artist in raw_artists:
                if isinstance(artist, str):
                    formatted_artists.append({"name": artist})
                elif isinstance(artist, dict):
                    formatted_artists.append(artist)

            normalized_anchors.append({
                "id": track.get("id"),
                "name": track.get("name"),
                "artists": formatted_artists,
                "spotify_uri": track.get("spotify_uri"),
                "anchor_type": "remix_source",
                "user_mentioned": False,
            })

        return normalized_anchors

    def get_optimized_mood_analysis(
        self, state: AgentState, is_remix: bool
    ) -> dict:
        """Get mood analysis for artist discovery, with optimization for remix mode.

        Args:
            state: Current agent state
            is_remix: Whether in remix mode

        Returns:
            Mood analysis dict (possibly limited for remix mode)
        """
        mood_analysis = state.mood_analysis

        if is_remix and mood_analysis:
            logger.info("Remix mode: limiting artist discovery scope")
            # Create a shallow copy with limited inputs to reduce search volume
            limited_analysis = mood_analysis.copy()
            if "genre_keywords" in limited_analysis:
                limited_analysis["genre_keywords"] = limited_analysis["genre_keywords"][:2]
            if "artist_recommendations" in limited_analysis:
                limited_analysis["artist_recommendations"] = limited_analysis["artist_recommendations"][:3]
            return limited_analysis

        return mood_analysis

    def limit_remix_tracks(self, remix_tracks: list, max_tracks: int = 30) -> list:
        """Limit remix tracks to reduce enrichment overhead.

        Args:
            remix_tracks: List of remix tracks
            max_tracks: Maximum number of tracks to keep

        Returns:
            Limited track list
        """
        if len(remix_tracks) > max_tracks:
            logger.info(f"Limiting remix tracks from {len(remix_tracks)} to {max_tracks} for processing")
            return remix_tracks[:max_tracks]
        return remix_tracks

    def get_artist_limit(self, is_remix: bool, default_limit: int = 15) -> int:
        """Get optimized artist limit for remix mode.

        Args:
            is_remix: Whether in remix mode
            default_limit: Default artist limit for normal mode

        Returns:
            Optimized artist limit
        """
        return 5 if is_remix else default_limit
