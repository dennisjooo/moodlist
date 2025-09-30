"""RecoBeat API service that coordinates all RecoBeat tools."""

import logging
from typing import Dict, List, Optional, Any

from .agent_tools import AgentTools
from .reccobeat.track_recommendations import TrackRecommendationsTool
from .reccobeat.track_info import GetMultipleTracksTool, GetTrackAudioFeaturesTool
from .reccobeat.artist_info import SearchArtistTool, GetMultipleArtistsTool


logger = logging.getLogger(__name__)


class RecoBeatService:
    """Service for coordinating RecoBeat API operations."""

    def __init__(self):
        """Initialize the RecoBeat service."""
        self.tools = AgentTools()

        # Register all RecoBeat tools
        self._register_tools()

        logger.info("Initialized RecoBeat service with all tools")

    def _register_tools(self):
        """Register all RecoBeat tools."""
        tools_to_register = [
            TrackRecommendationsTool(),
            GetMultipleTracksTool(),
            GetTrackAudioFeaturesTool(),
            SearchArtistTool(),
            GetMultipleArtistsTool()
        ]

        for tool in tools_to_register:
            self.tools.register_tool(tool)

    async def get_track_recommendations(
        self,
        seeds: List[str],
        size: int = 20,
        mood_features: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Get track recommendations with mood-based features.

        Args:
            seeds: List of track IDs to use as seeds
            size: Number of recommendations to return
            mood_features: Optional mood-based audio features
            **kwargs: Additional parameters for the API

        Returns:
            List of track recommendations
        """
        tool = self.tools.get_tool("get_track_recommendations")
        if not tool:
            raise ValueError("Track recommendations tool not available")

        # Merge mood features with kwargs
        if mood_features:
            api_params = {**mood_features, **kwargs}
        else:
            api_params = kwargs

        result = await tool._run(seeds=seeds, size=size, **api_params)

        if not result.success:
            logger.error(f"Failed to get recommendations: {result.error}")
            return []

        return result.data.get("recommendations", [])

    async def get_tracks_audio_features(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get audio features for multiple tracks.

        Args:
            track_ids: List of track IDs

        Returns:
            Dictionary mapping track IDs to their audio features
        """
        features_map = {}

        # Get audio features tool
        features_tool = self.tools.get_tool("get_track_audio_features")
        if not features_tool:
            logger.warning("Audio features tool not available")
            return features_map

        # Get features for each track
        for track_id in track_ids:
            try:
                result = await features_tool._run(track_id=track_id)
                if result.success:
                    features_map[track_id] = result.data
                else:
                    logger.warning(f"Failed to get features for track {track_id}: {result.error}")
            except Exception as e:
                logger.error(f"Error getting features for track {track_id}: {e}")

        return features_map

    async def search_artists_by_mood(self, mood_keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for artists that match mood keywords.

        Args:
            mood_keywords: List of mood-related keywords
            limit: Maximum number of artists to return

        Returns:
            List of matching artists
        """
        search_tool = self.tools.get_tool("search_artists")
        if not search_tool:
            logger.warning("Artist search tool not available")
            return []

        all_artists = []

        # Search for each mood keyword
        for keyword in mood_keywords:
            try:
                result = await search_tool._run(
                    search_text=keyword,
                    size=min(limit, 25)  # RecoBeat max per page
                )

                if result.success:
                    artists = result.data.get("artists", [])
                    all_artists.extend(artists)

                    # Break if we have enough artists
                    if len(all_artists) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error searching for artists with keyword '{keyword}': {e}")

        # Remove duplicates and limit results
        seen_ids = set()
        unique_artists = []
        for artist in all_artists:
            artist_id = artist.get("id")
            if artist_id and artist_id not in seen_ids:
                seen_ids.add(artist_id)
                unique_artists.append(artist)
                if len(unique_artists) >= limit:
                    break

        return unique_artists

    async def get_tracks_by_ids(self, track_ids: List[str]) -> List[Dict[str, Any]]:
        """Get track information for multiple track IDs.

        Args:
            track_ids: List of track IDs

        Returns:
            List of track information
        """
        # Split into chunks to respect API limits (40 per request)
        chunk_size = 40
        all_tracks = []

        for i in range(0, len(track_ids), chunk_size):
            chunk = track_ids[i:i + chunk_size]

            tracks_tool = self.tools.get_tool("get_multiple_tracks")
            if not tracks_tool:
                logger.warning("Multiple tracks tool not available")
                continue

            try:
                result = await tracks_tool._run(ids=chunk)
                if result.success:
                    tracks = result.data.get("tracks", [])
                    all_tracks.extend(tracks)
                else:
                    logger.warning(f"Failed to get tracks for chunk {i//chunk_size}: {result.error}")

            except Exception as e:
                logger.error(f"Error getting tracks for chunk {i//chunk_size}: {e}")

        return all_tracks

    def get_available_tools(self) -> List[str]:
        """Get list of available RecoBeat tools.

        Returns:
            List of tool names
        """
        return [
            "get_track_recommendations",
            "get_multiple_tracks",
            "get_track_audio_features",
            "search_artists",
            "get_multiple_artists"
        ]

    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available tools.

        Returns:
            Dictionary mapping tool names to descriptions
        """
        descriptions = {}

        for tool_name in self.get_available_tools():
            tool = self.tools.get_tool(tool_name)
            if tool:
                descriptions[tool_name] = tool.description

        return descriptions