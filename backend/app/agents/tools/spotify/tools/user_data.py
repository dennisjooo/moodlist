"""Spotify user data tools for the agentic system."""

import structlog
from typing import Type

from pydantic import BaseModel, Field

from ...agent_tools import RateLimitedTool, ToolResult


logger = structlog.get_logger(__name__)


class GetUserTopTracksInput(BaseModel):
    """Input schema for getting user's top tracks."""

    access_token: str = Field(..., description="Spotify access token")
    limit: int = Field(
        default=20, ge=1, le=50, description="Number of tracks to return"
    )
    time_range: str = Field(
        default="medium_term",
        description="Time range (short_term/medium_term/long_term)",
    )


class GetUserTopTracksTool(RateLimitedTool):
    """Tool for getting user's top tracks from Spotify API."""

    name: str = "get_user_top_tracks"
    description: str = """
    Get user's top tracks from Spotify API.
    Use this to gather seed tracks for recommendations based on user's listening history.
    """

    def __init__(self):
        """Initialize the user top tracks tool."""
        super().__init__(
            name="get_user_top_tracks",
            description="Get user's top tracks from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60,
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetUserTopTracksInput

    async def _run(
        self, access_token: str, limit: int = 20, time_range: str = "medium_term"
    ) -> ToolResult:
        """Get user's top tracks from Spotify.

        Args:
            access_token: Spotify access token
            limit: Number of tracks to return
            time_range: Time range for top tracks

        Returns:
            ToolResult with top tracks or error
        """
        try:
            logger.info(
                f"Getting top {limit} tracks for user (time_range: {time_range})"
            )

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/me/top/tracks",
                params={"limit": limit, "time_range": time_range},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # Validate response structure
            if not self._validate_response(response_data, ["items"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data,
                )

            # Parse tracks
            tracks = []
            for track_data in response_data["items"]:
                try:
                    track_info = {
                        "id": track_data.get("id"),
                        "name": track_data.get("name"),
                        "artists": [
                            artist.get("name")
                            for artist in track_data.get("artists", [])
                        ],
                        "spotify_uri": track_data.get("uri"),
                        "popularity": track_data.get("popularity", 50),
                        "preview_url": track_data.get("preview_url"),
                    }
                    tracks.append(track_info)

                except Exception as e:
                    logger.warning(
                        f"Failed to parse track data: {track_data}, error: {e}"
                    )
                    continue

            logger.info(f"Successfully retrieved {len(tracks)} top tracks")

            return ToolResult.success_result(
                data={
                    "tracks": tracks,
                    "total_count": len(tracks),
                    "time_range": time_range,
                    "limit": limit,
                },
                metadata={"source": "spotify", "api_endpoint": "/me/top/tracks"},
            )

        except Exception as e:
            logger.error(f"Error getting user top tracks: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get user top tracks: {str(e)}", error_type=type(e).__name__
            )


class GetUserTopArtistsInput(BaseModel):
    """Input schema for getting user's top artists."""

    access_token: str = Field(..., description="Spotify access token")
    limit: int = Field(
        default=20, ge=1, le=50, description="Number of artists to return"
    )
    time_range: str = Field(
        default="medium_term",
        description="Time range (short_term/medium_term/long_term)",
    )


class GetUserTopArtistsTool(RateLimitedTool):
    """Tool for getting user's top artists from Spotify API."""

    name: str = "get_user_top_artists"
    description: str = """
    Get user's top artists from Spotify API.
    Use this to gather seed artists for recommendations based on user's listening history.
    """

    def __init__(self):
        """Initialize the user top artists tool."""
        super().__init__(
            name="get_user_top_artists",
            description="Get user's top artists from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60,
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetUserTopArtistsInput

    async def _run(
        self, access_token: str, limit: int = 20, time_range: str = "medium_term"
    ) -> ToolResult:
        """Get user's top artists from Spotify.

        Args:
            access_token: Spotify access token
            limit: Number of artists to return
            time_range: Time range for top artists

        Returns:
            ToolResult with top artists or error
        """
        try:
            logger.info(
                f"Getting top {limit} artists for user (time_range: {time_range})"
            )

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/me/top/artists",
                params={"limit": limit, "time_range": time_range},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # Validate response structure
            if not self._validate_response(response_data, ["items"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data,
                )

            # Parse artists
            artists = []
            for artist_data in response_data["items"]:
                try:
                    artist_info = {
                        "id": artist_data.get("id"),
                        "name": artist_data.get("name"),
                        "spotify_uri": artist_data.get("uri"),
                        "genres": artist_data.get("genres", []),
                        "popularity": artist_data.get("popularity", 50),
                        "followers": artist_data.get("followers", {}).get("total", 0),
                    }
                    artists.append(artist_info)

                except Exception as e:
                    logger.warning(
                        f"Failed to parse artist data: {artist_data}, error: {e}"
                    )
                    continue

            logger.info(f"Successfully retrieved {len(artists)} top artists")

            return ToolResult.success_result(
                data={
                    "artists": artists,
                    "total_count": len(artists),
                    "time_range": time_range,
                    "limit": limit,
                },
                metadata={"source": "spotify", "api_endpoint": "/me/top/artists"},
            )

        except Exception as e:
            logger.error(f"Error getting user top artists: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get user top artists: {str(e)}", error_type=type(e).__name__
            )
