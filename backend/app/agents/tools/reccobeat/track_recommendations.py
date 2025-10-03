"""RecoBeat track recommendations tool."""

import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult
from ...states.agent_state import TrackRecommendation


logger = logging.getLogger(__name__)


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
            rate_limit_per_minute=120,  # Conservative: 2 requests/second
            min_request_interval=0.5  # Minimum 0.5s between requests to avoid bursts
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

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/v1/track/recommendation",
                params=params
            )

            # Validate response structure
            if not self._validate_response(response_data, ["content"]):
                return ToolResult.error_result(
                    "Invalid response structure from RecoBeat API",
                    api_response=response_data
                )

            # Parse recommendations
            recommendations = []
            for track_data in response_data["content"]:
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
                    
                    # Create recommendation object
                    recommendation = TrackRecommendation(
                        track_id=track_id,
                        track_name=track_name,
                        artists=artists,
                        spotify_uri=spotify_uri,
                        confidence_score=confidence_score,
                        audio_features={
                            "popularity": popularity,
                            "duration_ms": track_data.get("durationMs"),
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