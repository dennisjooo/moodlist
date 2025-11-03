"""Spotify track search tools."""

import structlog
from typing import Optional, Type

from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = structlog.get_logger(__name__)


class SearchSpotifyTracksInput(BaseModel):
    """Input schema for searching tracks on Spotify."""

    access_token: str = Field(..., description="Spotify access token")
    query: str = Field(..., description="Search query (track name, genre, keywords, etc.)")
    limit: int = Field(default=20, ge=1, le=50, description="Number of results to return")
    market: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code")


class SearchSpotifyTracksTool(RateLimitedTool):
    """Tool for searching tracks on Spotify API."""

    name: str = "search_spotify_tracks"
    description: str = """
    Search for tracks on Spotify by name, genre, or keywords.
    Use this to discover tracks that match mood keywords or genres.
    Returns track IDs, names, artists, and other track metadata.
    Supports genre filtering with 'genre:keyword' format.
    """

    def __init__(self):
        """Initialize the Spotify track search tool."""
        super().__init__(
            name="search_spotify_tracks",
            description="Search tracks on Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return SearchSpotifyTracksInput

    async def _run(
        self,
        access_token: str,
        query: str,
        limit: int = 20,
        market: Optional[str] = None
    ) -> ToolResult:
        """Search for tracks on Spotify.

        Args:
            access_token: Spotify access token
            query: Search query for tracks (can include 'genre:' prefix)
            limit: Number of results to return
            market: Optional ISO 3166-1 alpha-2 country code

        Returns:
            ToolResult with track search results or error
        """
        try:
            logger.info(f"Searching Spotify for tracks: '{query}' (limit: {limit})")

            # Build params
            params = {
                "q": query,
                "type": "track",
                "limit": limit
            }
            
            if market:
                params["market"] = market

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/search",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            if not self._validate_response(response_data, ["tracks"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse tracks from response
            tracks = []
            tracks_data = response_data.get("tracks", {})
            items = tracks_data.get("items", [])

            for track_data in items:
                try:
                    # Extract artist information
                    artists = []
                    for artist_data in track_data.get("artists", []):
                        artists.append({
                            "id": artist_data.get("id"),
                            "name": artist_data.get("name"),
                            "uri": artist_data.get("uri")
                        })

                    # Extract album information
                    album_data = track_data.get("album", {})
                    album = {
                        "id": album_data.get("id"),
                        "name": album_data.get("name"),
                        "uri": album_data.get("uri"),
                        "release_date": album_data.get("release_date"),
                        "images": album_data.get("images", [])
                    } if album_data else None

                    track_info = {
                        "id": track_data.get("id"),
                        "name": track_data.get("name"),
                        "spotify_uri": track_data.get("uri"),
                        "artists": artists,
                        "album": album,
                        "duration_ms": track_data.get("duration_ms"),
                        "popularity": track_data.get("popularity", 50),
                        "explicit": track_data.get("explicit", False),
                        "preview_url": track_data.get("preview_url"),
                        "track_number": track_data.get("track_number"),
                        "disc_number": track_data.get("disc_number", 1)
                    }
                    tracks.append(track_info)

                except Exception as e:
                    logger.warning(f"Failed to parse track data: {track_data}, error: {e}")
                    continue

            logger.info(f"Successfully found {len(tracks)} tracks for query '{query}'")

            return ToolResult.success_result(
                data={
                    "tracks": tracks,
                    "total_count": len(tracks),
                    "query": query,
                    "total_available": tracks_data.get("total", len(tracks))
                },
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/search",
                    "search_type": "track",
                    "result_count": len(tracks)
                }
            )

        except Exception as e:
            logger.error(f"Error searching Spotify tracks: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to search Spotify tracks: {str(e)}",
                error_type=type(e).__name__
            )

