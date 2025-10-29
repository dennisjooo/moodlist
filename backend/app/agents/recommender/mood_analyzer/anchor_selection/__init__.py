"""Anchor track selector for finding high-quality genre-specific tracks.

This module provides backward compatibility while using the new modular anchor selection engine.
"""
from typing import List, Dict, Any
from .selection_engine import AnchorSelectionEngine


class AnchorTrackSelector:
    """Selects anchor tracks from genre searches for feature reference and playlist inclusion.

    This class now serves as a backward-compatible wrapper around the new modular
    AnchorSelectionEngine. All functionality has been moved to the anchor_selection package.
    """

    def __init__(self, spotify_service=None, reccobeat_service=None, llm=None):
        """Initialize the anchor track selector.

        Args:
            spotify_service: SpotifyService for track search
            reccobeat_service: RecoBeatService for audio features
            llm: Language model for extracting user-mentioned tracks/artists
        """
        self.engine = AnchorSelectionEngine(spotify_service, reccobeat_service, llm)

    async def select_anchor_tracks(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str = "",
        artist_recommendations: List[str] = None,
        mood_analysis: Dict[str, Any] = None,
        limit: int = 5,
        user_mentioned_artists: List[str] = None
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Select anchor tracks using LLM-guided analysis instead of hard-coded logic.

        Args:
            genre_keywords: List of genre keywords to search
            target_features: Target audio features from mood analysis
            access_token: Spotify access token
            mood_prompt: Original user mood prompt for extracting track mentions
            artist_recommendations: List of artist names from mood analysis
            mood_analysis: Full mood analysis results for LLM context
            limit: Maximum number of anchor tracks to select (fallback if LLM doesn't specify)
            user_mentioned_artists: Artists explicitly mentioned by user from intent analysis (HIGHEST PRIORITY)

        Returns:
            Tuple of (anchor_tracks_for_playlist, anchor_track_ids_for_reference)
        """
        return await self.engine.select_anchor_tracks(
            genre_keywords, target_features, access_token, mood_prompt,
            artist_recommendations, mood_analysis, limit, user_mentioned_artists
        )
