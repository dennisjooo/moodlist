"""Anchor track selection and management.

This module handles:
- Selecting anchor tracks using mood analysis and genre keywords
- Normalizing anchor track metadata
- Caching anchor tracks for performance
- Calculating appropriate anchor limits based on user mentions
"""

from typing import List

import structlog

from ...core.cache import cache_manager
from ...states.agent_state import AgentState
from ..mood_analyzer.anchor_selection import AnchorTrackSelector

logger = structlog.get_logger(__name__)


class AnchorTrackManager:
    """Manages anchor track selection, normalization, and caching."""

    def __init__(self, anchor_track_selector: AnchorTrackSelector):
        """Initialize the anchor track manager.

        Args:
            anchor_track_selector: Service for selecting anchor tracks
        """
        self.anchor_track_selector = anchor_track_selector

    async def select_anchor_tracks(
        self,
        state: AgentState,
        intent_analysis: dict,
        access_token: str,
        limit_override: int = None,
    ) -> None:
        """Select anchor tracks using mood analysis and genre keywords.

        Args:
            state: Current agent state
            intent_analysis: Intent analysis
            access_token: Spotify access token
            limit_override: Optional limit override for optimization
        """
        logger.info("Selecting anchor tracks")

        try:
            # Optimization: Check cache for anchor tracks
            cached_anchors = await cache_manager.get_anchor_tracks(
                user_id=state.user_id, mood_prompt=state.mood_prompt
            )

            if cached_anchors is not None:
                logger.info(
                    f"Cache hit for anchor tracks - using {len(cached_anchors)} cached anchors"
                )
                normalized_anchors = self._normalize_anchor_tracks(
                    cached_anchors, state, intent_analysis
                )
                anchor_ids = [
                    track.get("id") for track in normalized_anchors if track.get("id")
                ]
                state.metadata["anchor_tracks"] = normalized_anchors
                state.metadata["anchor_track_ids"] = anchor_ids
                return

            # Cache miss - compute anchor tracks
            # Prepare anchor selection parameters
            anchor_params = self._prepare_anchor_selection_params(
                state, intent_analysis, access_token
            )

            # Apply limit override if provided
            if limit_override:
                anchor_params["limit"] = limit_override

            # Call anchor selection
            (
                anchor_tracks,
                anchor_ids,
            ) = await self.anchor_track_selector.select_anchor_tracks(**anchor_params)

            normalized_anchors = self._normalize_anchor_tracks(
                anchor_tracks, state, intent_analysis
            )

            # Store results
            state.metadata["anchor_tracks"] = normalized_anchors
            state.metadata["anchor_track_ids"] = [
                track.get("id") for track in normalized_anchors if track.get("id")
            ]

            # Optimization: Cache the anchor tracks
            if normalized_anchors:
                await cache_manager.set_anchor_tracks(
                    user_id=state.user_id,
                    mood_prompt=state.mood_prompt,
                    anchor_tracks=normalized_anchors,
                )
                logger.info(f"Cached {len(normalized_anchors)} anchor tracks")

            logger.info(f"✓ Selected {len(normalized_anchors)} anchor tracks")

        except Exception as e:
            logger.warning(f"Failed to select anchor tracks: {e}")
            state.metadata["anchor_tracks"] = []
            state.metadata["anchor_track_ids"] = []

    def _prepare_anchor_selection_params(
        self, state: AgentState, intent_analysis: dict, access_token: str
    ) -> dict:
        """Prepare parameters for anchor track selection.

        Args:
            state: Current agent state
            intent_analysis: Intent analysis data
            access_token: Spotify access token

        Returns:
            Dictionary of parameters for anchor selection
        """
        mood_analysis = state.mood_analysis or {}
        target_features = state.metadata.get("target_features", {})
        genre_keywords = mood_analysis.get("genre_keywords", [])
        artist_recommendations = mood_analysis.get("artist_recommendations", [])

        # Use intent analysis for stricter genre matching if available
        if intent_analysis.get("primary_genre"):
            genre_keywords = [intent_analysis["primary_genre"]] + genre_keywords

        # Extract user-mentioned artists from intent analysis (HIGHEST PRIORITY)
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])

        # Calculate appropriate anchor limit
        anchor_limit = self._calculate_anchor_limit(user_mentioned_artists)

        return {
            "genre_keywords": genre_keywords,
            "target_features": target_features,
            "access_token": access_token,
            "mood_prompt": state.mood_prompt,
            "artist_recommendations": artist_recommendations,
            "mood_analysis": mood_analysis,
            "limit": anchor_limit,
            "user_mentioned_artists": user_mentioned_artists,
        }

    def _normalize_anchor_tracks(
        self, anchor_tracks: List[dict], state: AgentState, intent_analysis: dict
    ) -> List[dict]:
        """Ensure anchor metadata correctly reflects actual user mentions.

        Args:
            anchor_tracks: Raw anchor tracks to normalize
            state: Current agent state
            intent_analysis: Intent analysis data

        Returns:
            Normalized anchor tracks with correct metadata
        """
        if not anchor_tracks:
            return []

        user_track_ids = set(state.metadata.get("user_mentioned_track_ids", []))
        user_mentioned_artists = {
            artist.lower()
            for artist in intent_analysis.get("user_mentioned_artists", [])
            if isinstance(artist, str)
        }

        normalized_tracks: List[dict] = []
        for anchor in anchor_tracks:
            if not isinstance(anchor, dict):
                continue

            normalized = dict(anchor)  # shallow copy
            track_id = normalized.get("id") or normalized.get("track_id")

            is_user_track = bool(track_id and track_id in user_track_ids)
            normalized["user_mentioned"] = is_user_track
            if is_user_track:
                normalized["anchor_type"] = "user"
                normalized["protected"] = True

            artist_names = []
            for artist in normalized.get("artists", []):
                if isinstance(artist, dict):
                    name = artist.get("name")
                else:
                    name = artist
                if name:
                    artist_names.append(name)

            normalized["user_mentioned_artist"] = any(
                name.lower() in user_mentioned_artists for name in artist_names
            )

            normalized_tracks.append(normalized)

        return normalized_tracks

    def _calculate_anchor_limit(self, user_mentioned_artists: list) -> int:
        """Calculate appropriate anchor limit based on user-mentioned artists.

        Args:
            user_mentioned_artists: List of artists mentioned by user

        Returns:
            Appropriate anchor limit
        """
        base_limit = 5

        if not user_mentioned_artists:
            return base_limit

        # Guarantee at least 2 tracks per user-mentioned artist, plus some genre anchors
        min_needed = len(user_mentioned_artists) * 2  # 2 tracks per artist
        anchor_limit = max(base_limit, min_needed + 2)  # +2 for genre diversity

        logger.info(
            f"✓ Passing {len(user_mentioned_artists)} user-mentioned artists to anchor selection: "
            f"{user_mentioned_artists} (limit increased from {base_limit} to {anchor_limit})"
        )

        return anchor_limit
