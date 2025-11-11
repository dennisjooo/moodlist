"""RecoBeat track information tools."""

import structlog
from typing import List, Type

from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = structlog.get_logger(__name__)


class GetMultipleTracksInput(BaseModel):
    """Input schema for getting multiple tracks."""

    ids: List[str] = Field(..., min_items=1, max_items=40, description="List of track IDs")


class GetMultipleTracksTool(RateLimitedTool):
    """Tool for getting multiple tracks from RecoBeat API."""

    name: str = "get_multiple_tracks"
    description: str = """
    Get detailed information for multiple tracks from RecoBeat API.
    Use this to fetch track metadata in bulk.
    """

    def __init__(self):
        """Initialize the multiple tracks tool."""
        super().__init__(
            name="get_multiple_tracks",
            description="Get multiple tracks from RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=120,   # More conservative rate limit
            min_request_interval=1.0,   # 1s between requests to avoid rate limiting
            use_global_semaphore=True,  # Use global semaphore to limit concurrent requests
            timeout=180                 # Increased to accommodate slow RecoBeat responses
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetMultipleTracksInput

    async def _run(self, ids: List[str]) -> ToolResult:
        """Get multiple tracks from RecoBeat.

        Args:
            ids: List of track IDs

        Returns:
            ToolResult with track data or error
        """
        try:
            logger.info(f"Getting {len(ids)} tracks from RecoBeat")

            # Make API request with caching (30 days TTL for track details - immutable metadata)
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/track",
                params={"ids": ids},
                use_cache=True,
                cache_ttl=2592000  # 30 days - track metadata is immutable
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
                    track_info = {
                        "id": track_data.get("id"),
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

            logger.info(f"Successfully retrieved {len(tracks)} tracks")

            return ToolResult.success_result(
                data={
                    "tracks": tracks,
                    "total_count": len(tracks),
                    "requested_count": len(ids)
                },
                metadata={
                    "source": "reccobeat",
                    "api_endpoint": "/v1/track"
                }
            )

        except Exception as e:
            # 404 errors are expected when Spotify IDs don't exist in RecoBeat
            if "404" in str(e):
                logger.debug("Some tracks not found in RecoBeat (404) - returning empty result")
                return ToolResult.success_result(
                    data={"tracks": [], "total_count": 0, "requested_count": len(ids)},
                    metadata={"source": "reccobeat", "api_endpoint": "/v1/track"}
                )
            else:
                logger.error(f"Error getting multiple tracks: {str(e)}", exc_info=True)
                return ToolResult.error_result(
                    f"Failed to get multiple tracks: {str(e)}",
                    error_type=type(e).__name__
                )


class GetTrackAudioFeaturesInput(BaseModel):
    """Input schema for getting track audio features."""

    track_id: str = Field(..., description="RecoBeat track ID")


class GetTrackAudioFeaturesTool(RateLimitedTool):
    """Tool for getting track audio features from RecoBeat API."""

    name: str = "get_track_audio_features"
    description: str = """
    Get detailed audio features for a specific track from RecoBeat API.
    Use this to analyze track characteristics for mood matching.
    """

    def __init__(self):
        """Initialize the audio features tool."""
        super().__init__(
            name="get_track_audio_features",
            description="Get track audio features from RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=50,   # More conservative: 50/min = ~0.83/sec to avoid hitting limits
            min_request_interval=1.0,   # Restore tighter spacing now that concurrency is controlled
            use_global_semaphore=True,  # Use global semaphore to limit concurrent requests
            timeout=180                 # Increased to accommodate slow RecoBeat responses
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetTrackAudioFeaturesInput

    async def _run(self, track_id: str) -> ToolResult:
        """Get audio features for a track from RecoBeat.

        Args:
            track_id: RecoBeat track ID

        Returns:
            ToolResult with audio features or error
        """
        try:
            logger.debug(f"Getting audio features for track {track_id}")

            # Make API request with caching (90 days TTL for audio features - immutable per track)
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/v1/track/{track_id}/audio-features",
                use_cache=True,
                cache_ttl=7776000  # 90 days - audio features never change for a track
            )

            # Validate response structure
            required_fields = [
                "acousticness", "danceability", "energy", "instrumentalness",
                "key", "liveness", "loudness", "mode", "speechiness", "tempo", "valence"
            ]

            if not self._validate_response(response_data, required_fields):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Parse audio features
            audio_features = {
                "track_id": response_data.get("id"),
                "spotify_uri": response_data.get("href"),
                "acousticness": response_data.get("acousticness"),
                "danceability": response_data.get("danceability"),
                "energy": response_data.get("energy"),
                "instrumentalness": response_data.get("instrumentalness"),
                "key": response_data.get("key"),
                "liveness": response_data.get("liveness"),
                "loudness": response_data.get("loudness"),
                "mode": response_data.get("mode"),
                "speechiness": response_data.get("speechiness"),
                "tempo": response_data.get("tempo"),
                "valence": response_data.get("valence")
            }

            logger.debug(f"Successfully retrieved audio features for track {track_id}")

            return ToolResult.success_result(
                data=audio_features,
                metadata={
                    "source": "reccobeat",
                    "track_id": track_id,
                    "api_endpoint": f"/v1/track/{track_id}/audio-features"
                }
            )

        except Exception as e:
            # 404 errors are expected for Spotify tracks not in RecoBeat database
            if "404" in str(e):
                logger.debug(f"Track {track_id} not found in RecoBeat (404) - this is normal for many Spotify tracks")
                return ToolResult.error_result(
                    f"Track not found in RecoBeat: {str(e)}",
                    error_type=type(e).__name__
                )
            else:
                logger.error(f"Error getting track audio features: {str(e)}", exc_info=True)
                return ToolResult.error_result(
                    f"Failed to get track audio features: {str(e)}",
                    error_type=type(e).__name__
                )