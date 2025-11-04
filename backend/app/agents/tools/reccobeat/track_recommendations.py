"""RecoBeat track recommendations tool."""

import structlog
from typing import List, Optional, Type

from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult
from ...states.agent_state import TrackRecommendation


logger = structlog.get_logger(__name__)


class TrackRecommendationsInput(BaseModel):
    """Input schema for track recommendations tool."""

    seeds: List[str] = Field(..., min_items=1, max_items=5, description="List of track IDs to use as seeds")
    size: int = Field(default=20, ge=1, le=100, description="Number of recommendations to return")
    negative_seeds: Optional[List[str]] = Field(default=None, max_items=5, description="Tracks to avoid")
    acousticness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Acousticness preference")
    danceability: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Danceability preference")
    energy: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Energy preference")
    instrumentalness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Instrumentalness preference")
    key: Optional[int] = Field(default=None, ge=-1, le=11, description="Musical key preference")
    liveness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Liveness preference")
    loudness: Optional[float] = Field(default=None, ge=-60.0, le=2.0, description="Loudness preference")
    mode: Optional[int] = Field(default=None, ge=0, le=1, description="Mode preference (0=minor, 1=major)")
    speechiness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Speechiness preference")
    tempo: Optional[float] = Field(default=None, ge=0.0, le=250.0, description="Tempo preference")
    valence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Valence preference")
    popularity: Optional[int] = Field(default=None, ge=0, le=100, description="Popularity preference")
    feature_weight: Optional[float] = Field(default=None, ge=1.0, le=5.0, description="Feature influence scaling")


class TrackRecommendationsTool(RateLimitedTool):
    """Tool for getting track recommendations from RecoBeat API."""

    name: str = "get_track_recommendations"
    description: str = """
    Get track recommendations from RecoBeat API based on seed tracks and audio features.
    Use this to find tracks that match a specific mood or musical style.
    """

    def __init__(self):
        """Initialize the track recommendations tool."""
        super().__init__(
            name="get_track_recommendations",
            description="Get track recommendations from RecoBeat API",
            base_url="https://api.reccobeats.com",
            rate_limit_per_minute=120,   # More conservative rate limit
            min_request_interval=1.0,   # 1s between requests to avoid rate limiting
            use_global_semaphore=True   # Use global semaphore to limit concurrent requests
        )

    def _normalize_spotify_uri(self, href: str, track_id: str) -> str:
        """Normalize Spotify URI from href or track ID.
        
        Args:
            href: URL or URI from RecoBeat
            track_id: Track ID as fallback
            
        Returns:
            Properly formatted Spotify URI
        """
        if not href and not track_id:
            return None
            
        # If href is already a proper URI
        if href and href.startswith('spotify:track:'):
            return href
            
        # If href is a URL, extract ID
        if href and 'spotify.com/track/' in href:
            track_id = href.split('/track/')[-1].split('?')[0]
            return f"spotify:track:{track_id}"
            
        # If href has spotify: prefix but wrong format
        if href and 'spotify:' in href:
            parts = href.split(':')
            if len(parts) >= 3:
                return f"spotify:track:{parts[-1]}"
        
        # Use track_id as fallback
        if track_id:
            # Remove any prefixes
            clean_id = track_id.split('/')[-1].split('?')[0]
            return f"spotify:track:{clean_id}"
            
        return None
    
    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return TrackRecommendationsInput

    def _validate_parameters(
        self,
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        size: int = 20
    ) -> Optional[str]:
        """Validate recommendation parameters to detect known-bad combinations.

        Phase 1 Optimization: Detect invalid parameter combinations early to avoid
        expensive API calls and retry loops.

        Args:
            seeds: List of seed track IDs
            negative_seeds: Optional list of negative seed track IDs
            size: Number of recommendations requested

        Returns:
            Error message if validation fails, None if parameters are valid
        """
        # Validate seeds are not empty strings
        if not seeds or any(not s or not s.strip() for s in seeds):
            return "Seeds contain empty or whitespace-only IDs"

        # Validate negative seeds if provided
        if negative_seeds:
            if any(not s or not s.strip() for s in negative_seeds):
                return "Negative seeds contain empty or whitespace-only IDs"

            # RecoBeat API fails when negative seeds >= positive seeds
            if len(negative_seeds) >= len(seeds):
                return f"Too many negative seeds ({len(negative_seeds)}) relative to positive seeds ({len(seeds)})"

            # Check for overlap between seeds and negative seeds
            seed_set = set(seeds)
            negative_set = set(negative_seeds)
            overlap = seed_set & negative_set
            if overlap:
                return f"Seeds and negative seeds contain overlapping IDs: {overlap}"

        # Validate size is reasonable
        if size < 1 or size > 100:
            return f"Invalid recommendation size: {size} (must be 1-100)"

        return None

    async def _get_track_details(self, track_ids: List[str]) -> dict[str, int]:
        """Get track details including duration_ms from /v1/track endpoint.

        Args:
            track_ids: List of RecoBeat track IDs

        Returns:
            Dictionary mapping track_id to duration_ms
        """
        if not track_ids:
            return {}

        try:
            # Make API request to get track details with caching (30 minutes TTL for track details)
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/track",
                params={"ids": track_ids},
                use_cache=True,
                cache_ttl=1800  # 30 minutes
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                logger.warning("Invalid response structure from track details API")
                return {}

            # Parse track details
            track_details = {}
            for track_data in response_data["content"]:
                try:
                    track_id = track_data.get("id")
                    duration_ms = track_data.get("durationMs")
                    if track_id and duration_ms:
                        track_details[track_id] = duration_ms
                except Exception as e:
                    logger.warning(f"Failed to parse track detail: {track_data}, error: {e}")
                    continue

            logger.info(f"Successfully retrieved details for {len(track_details)} tracks")
            return track_details

        except Exception as e:
            logger.error(f"Error getting track details: {str(e)}", exc_info=True)
            return {}

    async def _run(
        self,
        seeds: List[str],
        size: int = 20,
        negative_seeds: Optional[List[str]] = None,
        acousticness: Optional[float] = None,
        danceability: Optional[float] = None,
        energy: Optional[float] = None,
        instrumentalness: Optional[float] = None,
        key: Optional[int] = None,
        liveness: Optional[float] = None,
        loudness: Optional[float] = None,
        mode: Optional[int] = None,
        speechiness: Optional[float] = None,
        tempo: Optional[float] = None,
        valence: Optional[float] = None,
        popularity: Optional[int] = None,
        feature_weight: Optional[float] = None
    ) -> ToolResult:
        """Get track recommendations from RecoBeat.

        Args:
            seeds: List of track IDs to use as seeds
            size: Number of recommendations to return
            negative_seeds: Tracks to avoid
            acousticness: Acousticness preference (0-1)
            danceability: Danceability preference (0-1)
            energy: Energy preference (0-1)
            instrumentalness: Instrumentalness preference (0-1)
            key: Musical key preference (-1-11)
            liveness: Liveness preference (0-1)
            loudness: Loudness preference (-60-2)
            mode: Mode preference (0=minor, 1=major)
            speechiness: Speechiness preference (0-1)
            tempo: Tempo preference (0-250)
            valence: Valence preference (0-1)
            popularity: Popularity preference (0-100)
            feature_weight: Feature influence scaling (1-5)

        Returns:
            ToolResult with recommendations or error
        """
        try:
            # PHASE 1: Validate parameters to short-circuit known-bad combinations
            validation_error = self._validate_parameters(seeds, negative_seeds, size)
            if validation_error:
                logger.warning(f"Invalid recommendation parameters: {validation_error}")
                return ToolResult.error_result(
                    f"Invalid parameters: {validation_error}",
                    error_type="ValidationError",
                    skip_retry=True  # Don't retry validation failures
                )
            # Build query parameters
            params = {
                "seeds": seeds,
                "size": size
            }

            # Add optional parameters
            optional_params = {
                "negativeSeeds": negative_seeds,
                "acousticness": acousticness,
                "danceability": danceability,
                "energy": energy,
                "instrumentalness": instrumentalness,
                "key": key,
                "liveness": liveness,
                "loudness": loudness,
                "mode": mode,
                "speechiness": speechiness,
                "tempo": tempo,
                "valence": valence,
                "popularity": popularity,
                "featureWeight": feature_weight
            }

            # Only add non-None parameters
            for param_name, param_value in optional_params.items():
                if param_value is not None:
                    params[param_name] = param_value

            logger.info(f"Getting {size} recommendations for {len(seeds)} seeds")

            # Make API request with caching (5 minutes TTL for recommendations)
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/track/recommendation",
                params=params,
                use_cache=True,
                cache_ttl=300  # 5 minutes - recommendations can change but not too frequently
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Extract track IDs from recommendations for getting duration_ms from track endpoint
            track_ids = []
            recommendation_data = []
            for track_data in response_data["content"]:
                try:
                    track_id = track_data.get("id")
                    if track_id:
                        track_ids.append(track_id)
                        recommendation_data.append(track_data)
                except Exception as e:
                    logger.warning(f"Failed to extract track ID: {track_data}, error: {e}")
                    continue

            # Get track details including duration_ms from /v1/track endpoint
            track_details = await self._get_track_details(track_ids)
            logger.info(f"Retrieved duration_ms for {len(track_details)} tracks from track endpoint")

            # Parse recommendations using duration_ms from track endpoint
            recommendations = []
            for track_data in recommendation_data:
                try:
                    # Extract track information
                    track_id = track_data.get("id")
                    track_name = track_data.get("trackTitle", "Unknown Track")
                    artists = [artist.get("name", "Unknown Artist")
                              for artist in track_data.get("artists", [])]

                    # Extract and normalize Spotify URI
                    href = track_data.get("href", "")
                    spotify_uri = self._normalize_spotify_uri(href, track_id)

                    # Calculate confidence from popularity and relevance
                    popularity = track_data.get("popularity", 50)
                    relevance_score = track_data.get("relevanceScore", 0.8)  # RecoBeat's relevance

                    # Combine factors for final confidence
                    confidence_score = min(
                        (relevance_score * 0.6) + (popularity / 100.0 * 0.4),
                        1.0
                    )

                    # Get duration_ms from track endpoint, fallback to recommendations response
                    duration_ms = track_details.get(track_id, track_data.get("durationMs"))

                    # Create recommendation object
                    recommendation = TrackRecommendation(
                        track_id=track_id,
                        track_name=track_name,
                        artists=artists,
                        spotify_uri=spotify_uri,
                        confidence_score=confidence_score,
                        audio_features={
                            "popularity": popularity,
                            "duration_ms": duration_ms,
                            "relevance_score": relevance_score
                        },
                        reasoning=f"Recommended based on {len(seeds)} seed tracks (relevance: {int(relevance_score * 100)}%)",
                        source="reccobeat"
                    )

                    recommendations.append(recommendation)

                except Exception as e:
                    logger.warning(f"Failed to parse track data: {track_data}, error: {e}")
                    continue

            logger.info(f"Successfully retrieved {len(recommendations)} recommendations")

            return ToolResult.success_result(
                data={
                    "recommendations": [rec.dict() for rec in recommendations],
                    "total_count": len(recommendations),
                    "seed_count": len(seeds),
                    "api_params": params
                },
                metadata={
                    "source": "reccobeat",
                    "recommendation_count": len(recommendations),
                    "api_endpoint": "/v1/track/recommendation"
                }
            )

        except Exception as e:
            logger.error(f"Error getting track recommendations: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get track recommendations: {str(e)}",
                error_type=type(e).__name__
            )