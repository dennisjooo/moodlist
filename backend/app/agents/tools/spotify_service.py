"""Spotify API service that coordinates all Spotify tools."""

import logging
from typing import Dict, List, Optional, Any

from .agent_tools import AgentTools
from .spotify.user_data import GetUserTopTracksTool, GetUserTopArtistsTool
from .spotify.playlist_management import CreatePlaylistTool, AddTracksToPlaylistTool
from .spotify.user_profile import GetUserProfileTool


logger = logging.getLogger(__name__)


class SpotifyService:
    """Service for coordinating Spotify API operations."""

    def __init__(self):
        """Initialize the Spotify service."""
        self.tools = AgentTools()

        # Register all Spotify tools
        self._register_tools()

        logger.info("Initialized Spotify service with all tools")

    def _register_tools(self):
        """Register all Spotify tools."""
        tools_to_register = [
            GetUserTopTracksTool(),
            GetUserTopArtistsTool(),
            CreatePlaylistTool(),
            AddTracksToPlaylistTool(),
            GetUserProfileTool()
        ]

        for tool in tools_to_register:
            self.tools.register_tool(tool)

    async def get_user_top_tracks(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term"
    ) -> List[Dict[str, Any]]:
        """Get user's top tracks.

        Args:
            access_token: Spotify access token
            limit: Number of tracks to return
            time_range: Time range for analysis

        Returns:
            List of user's top tracks
        """
        tool = self.tools.get_tool("get_user_top_tracks")
        if not tool:
            raise ValueError("User top tracks tool not available")

        result = await tool._run(
            access_token=access_token,
            limit=limit,
            time_range=time_range
        )

        if not result.success:
            logger.error(f"Failed to get user top tracks: {result.error}")
            return []

        return result.data.get("tracks", [])

    async def get_user_top_artists(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term"
    ) -> List[Dict[str, Any]]:
        """Get user's top artists.

        Args:
            access_token: Spotify access token
            limit: Number of artists to return
            time_range: Time range for analysis

        Returns:
            List of user's top artists
        """
        tool = self.tools.get_tool("get_user_top_artists")
        if not tool:
            raise ValueError("User top artists tool not available")

        result = await tool._run(
            access_token=access_token,
            limit=limit,
            time_range=time_range
        )

        if not result.success:
            logger.error(f"Failed to get user top artists: {result.error}")
            return []

        return result.data.get("artists", [])

    async def get_user_profile(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user's Spotify profile.

        Args:
            access_token: Spotify access token

        Returns:
            User profile information or None if failed
        """
        tool = self.tools.get_tool("get_user_profile")
        if not tool:
            raise ValueError("User profile tool not available")

        result = await tool._run(access_token=access_token)

        if not result.success:
            logger.error(f"Failed to get user profile: {result.error}")
            return None

        return result.data

    async def create_playlist(
        self,
        access_token: str,
        name: str,
        description: str = "",
        public: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create a new playlist.

        Args:
            access_token: Spotify access token
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public

        Returns:
            Playlist information or None if failed
        """
        tool = self.tools.get_tool("create_playlist")
        if not tool:
            raise ValueError("Create playlist tool not available")

        result = await tool._run(
            access_token=access_token,
            name=name,
            description=description,
            public=public
        )

        if not result.success:
            logger.error(f"Failed to create playlist: {result.error}")
            return None

        return result.data

    async def add_tracks_to_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: List[str],
        position: Optional[int] = None
    ) -> bool:
        """Add tracks to a playlist.

        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            track_uris: List of track URIs to add
            position: Optional position for tracks

        Returns:
            Whether operation was successful
        """
        tool = self.tools.get_tool("add_tracks_to_playlist")
        if not tool:
            raise ValueError("Add tracks to playlist tool not available")

        result = await tool._run(
            access_token=access_token,
            playlist_id=playlist_id,
            track_uris=track_uris,
            position=position
        )

        if not result.success:
            logger.error(f"Failed to add tracks to playlist: {result.error}")
            return False

        return True

    def get_available_tools(self) -> List[str]:
        """Get list of available Spotify tools.

        Returns:
            List of tool names
        """
        return [
            "get_user_top_tracks",
            "get_user_top_artists",
            "get_user_profile",
            "create_playlist",
            "add_tracks_to_playlist"
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