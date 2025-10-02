"""Spotify artist search and discovery tools."""

import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = logging.getLogger(__name__)


class SearchSpotifyArtistsInput(BaseModel):
    """Input schema for searching artists on Spotify."""

    access_token: str = Field(..., description="Spotify access token")
    query: str = Field(..., description="Search query (artist name, genre, etc.)")
    limit: int = Field(default=20, ge=1, le=50, description="Number of results to return")


class SearchSpotifyArtistsTool(RateLimitedTool):
    """Tool for searching artists on Spotify API."""

    name: str = "search_spotify_artists"
    description: str = """
    Search for artists on Spotify by name, genre, or keywords.
    Use this to discover artists that match mood keywords or genres.
    Returns artist IDs, names, genres, and popularity.
    """

    def __init__(self):
        """Initialize the Spotify artist search tool."""
        super().__init__(
            name="search_spotify_artists",
            description="Search artists on Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return SearchSpotifyArtistsInput

    async def _run(
        self,
        access_token: str,
        query: str,
        limit: int = 20
    ) -> ToolResult:
        """Search for artists on Spotify.

        Args:
            access_token: Spotify access token
            query: Search query for artists
            limit: Number of results to return

        Returns:
            ToolResult with artist search results or error
        """
        try:
            logger.info(f"Searching Spotify for artists: '{query}' (limit: {limit})")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/search",
                params={
                    "q": query,
                    "type": "artist",
                    "limit": limit
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["artists"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse artists from response
            artists = []
            artists_data = response_data.get("artists", {})
            items = artists_data.get("items", [])

            for artist_data in items:
                try:
                    artist_info = {
                        "id": artist_data.get("id"),
                        "name": artist_data.get("name"),
                        "spotify_uri": artist_data.get("uri"),
                        "genres": artist_data.get("genres", []),
                        "popularity": artist_data.get("popularity", 50),
                        "followers": artist_data.get("followers", {}).get("total", 0),
                        "images": artist_data.get("images", [])
                    }
                    artists.append(artist_info)

                except Exception as e:
                    logger.warning(f"Failed to parse artist data: {artist_data}, error: {e}")
                    continue

            logger.info(f"Successfully found {len(artists)} artists for query '{query}'")

            return ToolResult.success_result(
                data={
                    "artists": artists,
                    "total_count": len(artists),
                    "query": query,
                    "total_available": artists_data.get("total", len(artists))
                },
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/search",
                    "search_type": "artist",
                    "result_count": len(artists)
                }
            )

        except Exception as e:
            logger.error(f"Error searching Spotify artists: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to search Spotify artists: {str(e)}",
                error_type=type(e).__name__
            )


class GetArtistTopTracksInput(BaseModel):
    """Input schema for getting an artist's top tracks."""

    access_token: str = Field(..., description="Spotify access token")
    artist_id: str = Field(..., description="Spotify artist ID")
    market: str = Field(default="US", description="ISO 3166-1 alpha-2 country code")


class GetArtistTopTracksTool(RateLimitedTool):
    """Tool for getting an artist's top tracks from Spotify API."""

    name: str = "get_artist_top_tracks"
    description: str = """
    Get an artist's top tracks from Spotify.
    Use this to fetch the most popular tracks from a specific artist.
    Returns up to 10 top tracks with full track metadata.
    """

    def __init__(self):
        """Initialize the get artist top tracks tool."""
        super().__init__(
            name="get_artist_top_tracks",
            description="Get artist's top tracks from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetArtistTopTracksInput

    async def _run(
        self,
        access_token: str,
        artist_id: str,
        market: str = "US"
    ) -> ToolResult:
        """Get an artist's top tracks from Spotify.

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: ISO 3166-1 alpha-2 country code

        Returns:
            ToolResult with top tracks or error
        """
        try:
            logger.info(f"Getting top tracks for artist {artist_id}")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/artists/{artist_id}/top-tracks",
                params={"market": market},
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["tracks"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse tracks
            tracks = []
            for track_data in response_data.get("tracks", []):
                try:
                    track_info = {
                        "id": track_data.get("id"),
                        "name": track_data.get("name"),
                        "spotify_uri": track_data.get("uri"),
                        "duration_ms": track_data.get("duration_ms"),
                        "popularity": track_data.get("popularity", 50),
                        "explicit": track_data.get("explicit", False),
                        "preview_url": track_data.get("preview_url"),
                        "track_number": track_data.get("track_number"),
                        "artists": [
                            {
                                "id": artist.get("id"),
                                "name": artist.get("name"),
                                "uri": artist.get("uri")
                            }
                            for artist in track_data.get("artists", [])
                        ],
                        "album": {
                            "id": track_data.get("album", {}).get("id"),
                            "name": track_data.get("album", {}).get("name"),
                            "uri": track_data.get("album", {}).get("uri"),
                            "release_date": track_data.get("album", {}).get("release_date")
                        } if track_data.get("album") else None
                    }
                    tracks.append(track_info)

                except Exception as e:
                    logger.warning(f"Failed to parse track data: {track_data}, error: {e}")
                    continue

            logger.info(f"Successfully retrieved {len(tracks)} top tracks for artist {artist_id}")

            return ToolResult.success_result(
                data={
                    "tracks": tracks,
                    "total_count": len(tracks),
                    "artist_id": artist_id
                },
                metadata={
                    "source": "spotify",
                    "api_endpoint": f"/artists/{artist_id}/top-tracks",
                    "market": market
                }
            )

        except Exception as e:
            logger.error(f"Error getting artist top tracks: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get artist top tracks: {str(e)}",
                error_type=type(e).__name__
            )


class GetSeveralSpotifyArtistsInput(BaseModel):
    """Input schema for getting multiple artists from Spotify."""

    access_token: str = Field(..., description="Spotify access token")
    artist_ids: List[str] = Field(..., min_items=1, max_items=50, description="List of artist IDs")


class GetSeveralSpotifyArtistsTool(RateLimitedTool):
    """Tool for getting multiple artists from Spotify API."""

    name: str = "get_several_spotify_artists"
    description: str = """
    Get detailed information for multiple artists from Spotify API.
    Use this to fetch full artist metadata including genres in bulk.
    Supports up to 50 artists per request.
    """

    def __init__(self):
        """Initialize the get several artists tool."""
        super().__init__(
            name="get_several_spotify_artists",
            description="Get multiple artists from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetSeveralSpotifyArtistsInput

    async def _run(
        self,
        access_token: str,
        artist_ids: List[str]
    ) -> ToolResult:
        """Get multiple artists from Spotify.

        Args:
            access_token: Spotify access token
            artist_ids: List of Spotify artist IDs

        Returns:
            ToolResult with artist data or error
        """
        try:
            logger.info(f"Getting {len(artist_ids)} artists from Spotify")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/artists",
                params={"ids": ",".join(artist_ids)},
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["artists"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse artists
            artists = []
            for artist_data in response_data.get("artists", []):
                if not artist_data:  # Skip null entries
                    continue

                try:
                    artist_info = {
                        "id": artist_data.get("id"),
                        "name": artist_data.get("name"),
                        "spotify_uri": artist_data.get("uri"),
                        "genres": artist_data.get("genres", []),
                        "popularity": artist_data.get("popularity", 50),
                        "followers": artist_data.get("followers", {}).get("total", 0),
                        "images": artist_data.get("images", [])
                    }
                    artists.append(artist_info)

                except Exception as e:
                    logger.warning(f"Failed to parse artist data: {artist_data}, error: {e}")
                    continue

            logger.info(f"Successfully retrieved {len(artists)} artists from Spotify")

            return ToolResult.success_result(
                data={
                    "artists": artists,
                    "total_count": len(artists),
                    "requested_count": len(artist_ids)
                },
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/artists"
                }
            )

        except Exception as e:
            logger.error(f"Error getting several Spotify artists: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get several Spotify artists: {str(e)}",
                error_type=type(e).__name__
            )

