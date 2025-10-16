"""Spotify playlist management tools for the agentic system."""

import structlog
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = structlog.get_logger(__name__)


class CreatePlaylistInput(BaseModel):
    """Input schema for creating a playlist."""

    access_token: str = Field(..., description="Spotify access token")
    name: str = Field(..., description="Playlist name")
    description: str = Field(default="", description="Playlist description")
    public: bool = Field(default=True, description="Whether playlist is public")


class CreatePlaylistTool(RateLimitedTool):
    """Tool for creating playlists on Spotify."""

    name: str = "create_playlist"
    description: str = """
    Create a new playlist on Spotify for the user.
    Use this to create playlists for recommended tracks.
    """

    def __init__(self):
        """Initialize the create playlist tool."""
        super().__init__(
            name="create_playlist",
            description="Create playlist on Spotify",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return CreatePlaylistInput

    async def _run(
        self,
        access_token: str,
        name: str,
        description: str = "",
        public: bool = True
    ) -> ToolResult:
        """Create a playlist on Spotify.

        Args:
            access_token: Spotify access token
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public

        Returns:
            ToolResult with playlist data or error
        """
        try:
            logger.info(f"Creating playlist '{name}' for user")

            # Prepare request data
            playlist_data = {
                "name": name,
                "description": description,
                "public": public
            }

            # Make API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/me/playlists",
                json_data=playlist_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            required_fields = ["id", "name", "uri"]
            if not self._validate_response(response_data, required_fields):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse playlist data
            playlist_info = {
                "id": response_data.get("id"),
                "name": response_data.get("name"),
                "description": response_data.get("description", ""),
                "spotify_uri": response_data.get("uri"),
                "external_urls": response_data.get("external_urls", {}),
                "public": response_data.get("public", False),
                "snapshot_id": response_data.get("snapshot_id")
            }

            logger.info(f"Successfully created playlist '{name}' with ID: {playlist_info['id']}")

            return ToolResult.success_result(
                data=playlist_info,
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/me/playlists"
                }
            )

        except Exception as e:
            logger.error(f"Error creating playlist: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to create playlist: {str(e)}",
                error_type=type(e).__name__
            )


class AddTracksToPlaylistInput(BaseModel):
    """Input schema for adding tracks to playlist."""

    access_token: str = Field(..., description="Spotify access token")
    playlist_id: str = Field(..., description="Spotify playlist ID")
    track_uris: List[str] = Field(..., description="List of Spotify track URIs to add")
    position: Optional[int] = Field(default=None, description="Position to add tracks")


class AddTracksToPlaylistTool(RateLimitedTool):
    """Tool for adding tracks to Spotify playlists."""

    name: str = "add_tracks_to_playlist"
    description: str = """
    Add tracks to a Spotify playlist.
    Use this to populate playlists with recommended tracks.
    """

    def __init__(self):
        """Initialize the add tracks tool."""
        super().__init__(
            name="add_tracks_to_playlist",
            description="Add tracks to Spotify playlist",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return AddTracksToPlaylistInput

    async def _run(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: List[str],
        position: Optional[int] = None
    ) -> ToolResult:
        """Add tracks to a Spotify playlist.

        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            track_uris: List of Spotify track URIs to add
            position: Optional position to add tracks

        Returns:
            ToolResult with result data or error
        """
        try:
            logger.info(f"Adding {len(track_uris)} tracks to playlist {playlist_id}")
            
            # Validate track URIs format
            invalid_uris = [uri for uri in track_uris if not uri or not uri.startswith('spotify:track:')]
            if invalid_uris:
                logger.error(f"Found {len(invalid_uris)} invalid URIs: {invalid_uris[:3]}")
                return ToolResult.error_result(
                    f"Invalid track URI format. Expected 'spotify:track:ID', got: {invalid_uris[:3]}",
                    error_type="ValidationError"
                )
            
            # Log sample URIs for debugging
            logger.debug(f"Sample URIs being added: {track_uris[:3]}")

            # Prepare request data
            request_data = {"uris": track_uris}
            if position is not None:
                request_data["position"] = position

            # Make API request
            response_data = await self._make_request(
                method="POST",
                endpoint=f"/playlists/{playlist_id}/tracks",
                json_data=request_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["snapshot_id"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse response
            result_info = {
                "playlist_id": playlist_id,
                "snapshot_id": response_data.get("snapshot_id"),
                "tracks_added": len(track_uris),
                "track_uris": track_uris[:5] + ["..."] if len(track_uris) > 5 else track_uris  # Truncate for logging
            }

            logger.info(f"Successfully added {len(track_uris)} tracks to playlist {playlist_id}")

            return ToolResult.success_result(
                data=result_info,
                metadata={
                    "source": "spotify",
                    "api_endpoint": f"/playlists/{playlist_id}/tracks"
                }
            )

        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to add tracks to playlist: {str(e)}",
                error_type=type(e).__name__
            )