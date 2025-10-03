"""RecoBeat artist information tools."""

import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = logging.getLogger(__name__)


class SearchArtistInput(BaseModel):
    """Input schema for searching artists."""

    search_text: str = Field(..., max_length=1000, description="Artist name to search for")
    page: int = Field(default=0, ge=0, le=1000, description="Page number")
    size: int = Field(default=25, ge=1, le=50, description="Results per page")


class SearchArtistTool(RateLimitedTool):
    """Tool for searching artists on RecoBeat API."""

    name: str = "search_artists"
    description: str = """
    Search for artists on RecoBeat API by name.
    Use this to find artists that match mood keywords or genres.
    """

    def __init__(self):
        """Initialize the artist search tool."""
        super().__init__(
            name="search_artists",
            description="Search artists on RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=120,  # Conservative: 2 requests/second
            min_request_interval=0.5  # Minimum 0.5s between requests to avoid bursts
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return SearchArtistInput

    async def _run(
        self,
        search_text: str,
        page: int = 0,
        size: int = 25
    ) -> ToolResult:
        """Search for artists on RecoBeat.

        Args:
            search_text: Artist name to search for
            page: Page number for pagination
            size: Number of results per page

        Returns:
            ToolResult with artist search results or error
        """
        try:
            logger.info(f"Searching for artists: '{search_text}' (page {page}, size {size})")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/artist/search",
                params={
                    "searchText": search_text,
                    "page": page,
                    "size": size
                }
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Parse artists
            artists = []
            for artist_data in response_data["content"]:
                try:
                    artist_info = {
                        "id": artist_data.get("id"),
                        "name": artist_data.get("name"),
                        "spotify_uri": artist_data.get("href")
                    }
                    artists.append(artist_info)

                except Exception as e:
                    logger.warning(f"Failed to parse artist data: {artist_data}, error: {e}")
                    continue

            # Get pagination info
            pagination = {
                "page": response_data.get("page", page),
                "size": response_data.get("size", size),
                "total_elements": response_data.get("totalElements", 0),
                "total_pages": response_data.get("totalPages", 0)
            }

            logger.info(f"Successfully found {len(artists)} artists for '{search_text}'")

            return ToolResult.success_result(
                data={
                    "artists": artists,
                    "pagination": pagination,
                    "search_text": search_text
                },
                metadata={
                    "source": "reccobeat",
                    "search_text": search_text,
                    "result_count": len(artists),
                    "api_endpoint": "/v1/artist/search"
                }
            )

        except Exception as e:
            logger.error(f"Error searching artists: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to search artists: {str(e)}",
                error_type=type(e).__name__
            )


class GetMultipleArtistsInput(BaseModel):
    """Input schema for getting multiple artists."""

    ids: List[str] = Field(..., min_items=1, max_items=40, description="List of artist IDs")


class GetMultipleArtistsTool(RateLimitedTool):
    """Tool for getting multiple artists from RecoBeat API."""

    name: str = "get_multiple_artists"
    description: str = """
    Get detailed information for multiple artists from RecoBeat API.
    Use this to fetch artist metadata in bulk.
    """

    def __init__(self):
        """Initialize the multiple artists tool."""
        super().__init__(
            name="get_multiple_artists",
            description="Get multiple artists from RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=120,  # Conservative: 2 requests/second
            min_request_interval=0.5  # Minimum 0.5s between requests to avoid bursts
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetMultipleArtistsInput

    async def _run(self, ids: List[str]) -> ToolResult:
        """Get multiple artists from RecoBeat.

        Args:
            ids: List of artist IDs

        Returns:
            ToolResult with artist data or error
        """
        try:
            logger.info(f"Getting {len(ids)} artists from RecoBeat")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/artist",
                params={"ids": ids}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Parse artists
            artists = []
            for artist_data in response_data["content"]:
                try:
                    artist_info = {
                        "id": artist_data.get("id"),
                        "name": artist_data.get("name"),
                        "spotify_uri": artist_data.get("href")
                    }
                    artists.append(artist_info)

                except Exception as e:
                    logger.warning(f"Failed to parse artist data: {artist_data}, error: {e}")
                    continue

            logger.info(f"Successfully retrieved {len(artists)} artists")

            return ToolResult.success_result(
                data={
                    "artists": artists,
                    "total_count": len(artists),
                    "requested_count": len(ids)
                },
                metadata={
                    "source": "reccobeat",
                    "api_endpoint": "/v1/artist"
                }
            )

        except Exception as e:
            logger.error(f"Error getting multiple artists: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get multiple artists: {str(e)}",
                error_type=type(e).__name__
            )


class GetArtistTracksInput(BaseModel):
    """Input schema for getting artist's tracks."""

    artist_id: str = Field(..., description="RecoBeat artist ID")
    page: int = Field(default=0, ge=0, le=1000, description="Page number")
    size: int = Field(default=25, ge=1, le=50, description="Tracks per page")


class GetArtistTracksTool(RateLimitedTool):
    """Tool for getting tracks from a specific artist on RecoBeat API."""

    name: str = "get_artist_tracks"
    description: str = """
    Get tracks from a specific artist on RecoBeat API.
    Use this to fetch an artist's catalog for mood-based recommendations.
    """

    def __init__(self):
        """Initialize the artist tracks tool."""
        super().__init__(
            name="get_artist_tracks",
            description="Get artist's tracks from RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=120,  # Conservative: 2 requests/second
            min_request_interval=0.5  # Minimum 0.5s between requests to avoid bursts
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetArtistTracksInput

    async def _run(
        self,
        artist_id: str,
        page: int = 0,
        size: int = 25
    ) -> ToolResult:
        """Get tracks from an artist on RecoBeat.

        Args:
            artist_id: RecoBeat artist ID
            page: Page number for pagination
            size: Number of tracks per page

        Returns:
            ToolResult with artist tracks or error
        """
        try:
            logger.info(f"Getting tracks for artist {artist_id} (page {page}, size {size})")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/v1/artist/{artist_id}/track",
                params={
                    "page": page,
                    "size": size
                }
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Parse tracks
            tracks = []
            for track_data in response_data["content"]:
                try:
                    # Normalize track ID (could be 'id' or 'trackId')
                    track_id = track_data.get("id") or track_data.get("track_id")
                    
                    track_info = {
                        "id": track_id,
                        "track_id": track_id,  # Include both for compatibility
                        "title": track_data.get("trackTitle"),
                        "artists": [artist.get("name") for artist in track_data.get("artists", [])],
                        "duration_ms": track_data.get("durationMs"),
                        "spotify_uri": track_data.get("href"),
                        "popularity": track_data.get("popularity", 50),
                        "isrc": track_data.get("isrc"),
                        "available_countries": track_data.get("availableCountries")
                    }
                    tracks.append(track_info)

                except Exception as e:
                    logger.warning(f"Failed to parse track data: {track_data}, error: {e}")
                    continue

            # Get pagination info
            pagination = {
                "page": response_data.get("page", page),
                "size": response_data.get("size", size),
                "total_elements": response_data.get("totalElements", 0),
                "total_pages": response_data.get("totalPages", 0)
            }

            logger.info(f"Successfully retrieved {len(tracks)} tracks for artist {artist_id}")

            return ToolResult.success_result(
                data={
                    "tracks": tracks,
                    "pagination": pagination,
                    "artist_id": artist_id,
                    "total_count": len(tracks)
                },
                metadata={
                    "source": "reccobeat",
                    "artist_id": artist_id,
                    "result_count": len(tracks),
                    "api_endpoint": f"/v1/artist/{artist_id}/track"
                }
            )

        except Exception as e:
            logger.error(f"Error getting artist tracks: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get artist tracks: {str(e)}",
                error_type=type(e).__name__
            )