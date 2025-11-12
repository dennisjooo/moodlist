"""Spotify artist search and discovery tools."""

import asyncio
import structlog
from typing import List, Type, Dict, Any, Optional, Tuple

from pydantic import BaseModel, Field

from ...agent_tools import RateLimitedTool, ToolResult
from ..utils.rate_limiting import wait_for_artist_top_tracks_rate_limit
from ..utils.track_parsing import parse_track_data
from ..utils.params_utils import build_market_params, get_market_label
from ..utils.album_operations import get_artist_albums, sample_album_tracks
from ..utils.track_operations import search_artist_tracks


logger = structlog.get_logger(__name__)


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

            # Make API request with caching enabled (15 min TTL)
            response_data = await self._make_request(
                method="GET",
                endpoint="/search",
                params={
                    "q": query,
                    "type": "artist",
                    "limit": limit
                },
                headers={"Authorization": f"Bearer {access_token}"},
                use_cache=True,
                cache_ttl=900  # 15 minutes - artist data doesn't change frequently
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
    market: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code (optional, defaults to global)")


class BatchGetArtistTopTracksInput(BaseModel):
    """Input schema for batching artist top tracks requests."""

    access_token: str = Field(..., description="Spotify access token")
    artist_ids: List[str] = Field(..., min_items=1, max_items=20, description="Artist IDs to fetch top tracks for")
    market: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-2 country code (optional, defaults to global)")


class BatchGetArtistTopTracksTool(RateLimitedTool):
    """Tool for parallel fetching of multiple artists' top tracks.
    
    Note: Spotify doesn't have a batch endpoint, so this tool makes parallel
    individual requests with concurrency control to respect rate limits.
    """

    name: str = "batch_get_artist_top_tracks"
    description: str = """
    Fetch multiple artists' top tracks in parallel using individual API requests.
    This uses parallel requests with concurrency control to optimize throughput
    while respecting Spotify's rate limits.
    """

    def __init__(self):
        """Initialize the batch artist top tracks tool."""
        super().__init__(
            name="batch_get_artist_top_tracks",
            description="Batch artist top tracks from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=100,  # High limit since global rate limiter handles actual spacing
            min_request_interval=0.1,  # Low interval since global rate limiter enforces 1.5s
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return BatchGetArtistTopTracksInput

    async def _run(
        self,
        access_token: str,
        artist_ids: List[str],
        market: Optional[str] = None,
    ) -> ToolResult:
        """Fetch top tracks for multiple artists in parallel."""

        if not artist_ids:
            return ToolResult.error_result("No artist IDs provided", skip_retry=True)

        unique_artist_ids = list(dict.fromkeys(artist_ids))
        
        # Use semaphore to control concurrency (2 concurrent requests to work with rate limiter)
        # With min_request_interval=1.2s, this ensures we don't overwhelm the rate limiter
        semaphore = asyncio.Semaphore(2)
        
        async def fetch_artist_tracks(artist_id: str) -> Tuple[str, List[Dict[str, Any]]]:
            """Fetch tracks for a single artist."""
            async with semaphore:
                try:
                    # Use global rate limiter to prevent overwhelming Spotify API
                    await wait_for_artist_top_tracks_rate_limit()
                    
                    # Build params using utility
                    params = build_market_params(market=market)
                    
                    # Make individual API request
                    response_data = await self._make_request(
                        method="GET",
                        endpoint=f"/artists/{artist_id}/top-tracks",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    # Parse tracks
                    tracks = []
                    for track_data in response_data.get("tracks", []):
                        try:
                            track_info = parse_track_data(track_data)
                            tracks.append(track_info)
                        except Exception as e:
                            logger.warning(f"Failed to parse track data for artist {artist_id}: {e}")
                            continue
                    
                    return artist_id, tracks
                except Exception as e:
                    logger.warning(f"Failed to fetch top tracks for artist {artist_id}: {e}")
                    return artist_id, []
        
        try:
            # Fetch all artists in parallel
            tasks = [fetch_artist_tracks(artist_id) for artist_id in unique_artist_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            artist_tracks: Dict[str, List[Dict[str, Any]]] = {}
            failed_artists: List[str] = []
            
            for result in results:
                if isinstance(result, Exception):
                    # If gather returned an exception, we can't identify which artist failed
                    logger.error(f"Unexpected error in batch fetch: {result}")
                    continue
                
                artist_id, tracks = result
                if tracks:
                    artist_tracks[artist_id] = tracks
                else:
                    failed_artists.append(artist_id)

            logger.info(
                "Batch artist top tracks fetched",
                requested=len(unique_artist_ids),
                succeeded=len(artist_tracks),
                failed=len(failed_artists),
            )

            return ToolResult.success_result(
                data={
                    "artist_tracks": artist_tracks,
                    "failed_artist_ids": failed_artists,
                },
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/artists/{id}/top-tracks",
                    "requested_count": len(unique_artist_ids),
                    "succeeded": len(artist_tracks),
                    "method": "parallel_individual_requests",
                },
            )

        except Exception as e:
            logger.error(f"Error during batch artist top tracks fetch: {e}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to batch fetch artist top tracks: {e}",
                error_type=type(e).__name__,
            )


class GetArtistTopTracksTool(RateLimitedTool):
    """Tool for getting an artist's top tracks from Spotify API.

    Supports hybrid track fetching strategy that combines:
    - Top tracks (filtered to avoid mega-hits)
    - Album deep cuts for diversity
    """

    name: str = "get_artist_top_tracks"
    description: str = """
    Get an artist's top tracks from Spotify.
    Use this to fetch the most popular tracks from a specific artist.
    Returns up to 10 top tracks with full track metadata.
    Supports hybrid mode for better track diversity.
    """

    def __init__(self):
        """Initialize the get artist top tracks tool."""
        super().__init__(
            name="get_artist_top_tracks",
            description="Get artist's top tracks from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=100,  # High limit since global rate limiter handles actual spacing
            min_request_interval=0.1,  # Low interval since global rate limiter enforces 1.5s
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetArtistTopTracksInput

    async def _run(
        self,
        access_token: str,
        artist_id: str,
        market: Optional[str] = None
    ) -> ToolResult:
        """Get an artist's top tracks from Spotify.

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: Optional ISO 3166-1 alpha-2 country code (None for global)

        Returns:
            ToolResult with top tracks or error
        """
        # Strategy 1: Try top-tracks endpoint (global if market is None)
        result = await self._try_top_tracks(access_token, artist_id, market)
        if result.success:
            return result

        # Strategy 2: If failed, fallback to search by artist name
        logger.warning(f"Failed to get top tracks for artist {artist_id}, trying search fallback")
        return await self._try_search_fallback(access_token, artist_id, market)

    async def _try_top_tracks(
        self,
        access_token: str,
        artist_id: str,
        market: Optional[str]
    ) -> ToolResult:
        """Try getting top tracks using the top-tracks endpoint (global if market is None)."""
        try:
            market_label = get_market_label(market)
            logger.info(f"Getting top tracks for artist {artist_id} (market: {market_label})")

            # Use global rate limiter to prevent overwhelming Spotify API
            await wait_for_artist_top_tracks_rate_limit()
            
            # Build params using utility
            params = build_market_params(market=market)
            
            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/artists/{artist_id}/top-tracks",
                params=params,
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
                    track_info = parse_track_data(track_data)
                    tracks.append(track_info)
                except Exception as e:
                    logger.warning(f"Failed to parse track data: {track_data}, error: {e}")
                    continue

            # Return success if we got tracks
            if tracks:
                logger.info(f"Successfully retrieved {len(tracks)} top tracks for artist {artist_id} (market: {market_label})")
                return ToolResult.success_result(
                    data={
                        "tracks": tracks,
                        "total_count": len(tracks),
                        "artist_id": artist_id
                    },
                    metadata={
                        "source": "spotify",
                        "api_endpoint": f"/artists/{artist_id}/top-tracks",
                        "market": market,
                        "strategy": "top_tracks"
                    }
                )
            else:
                logger.warning(f"No tracks found for artist {artist_id} (market: {market_label})")
                return ToolResult.error_result(
                    f"No tracks available for artist {artist_id}",
                    api_response=response_data
                )

        except Exception as e:
            logger.error(f"Error getting artist top tracks: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get artist top tracks: {str(e)}",
                error_type=type(e).__name__
            )

    async def _try_search_fallback(
        self,
        access_token: str,
        artist_id: str,
        market: Optional[str]
    ) -> ToolResult:
        """Fallback strategy: get artist name and search for tracks."""
        try:
            # First, get the artist name
            logger.info(f"Getting artist name for ID {artist_id} to perform search fallback")

            artist_response = await self._make_request(
                method="GET",
                endpoint=f"/artists/{artist_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if not self._validate_response(artist_response, []):
                return ToolResult.error_result(
                    "Failed to get artist information for search fallback",
                    api_response=artist_response
                )

            artist_name = artist_response.get("name")
            if not artist_name:
                return ToolResult.error_result(
                    "Could not retrieve artist name for search fallback"
                )

            logger.info(f"Retrieved artist name '{artist_name}' for search fallback")

            # Use the new track_operations utility
            result = await search_artist_tracks(
                make_request=self._make_request,
                validate_response=self._validate_response,
                access_token=access_token,
                artist_id=artist_id,
                artist_name=artist_name,
                market=market,
                limit=20
            )

            if result and result.get("tracks"):
                tracks = result["tracks"]
                logger.info(f"Successfully retrieved {len(tracks)} tracks for artist {artist_name} via search fallback")
                return ToolResult.success_result(
                    data={
                        "tracks": tracks,
                        "total_count": len(tracks),
                        "artist_id": artist_id
                    },
                    metadata={
                        "source": "spotify",
                        "api_endpoint": "/search",
                        "market": market,
                        "artist_name": artist_name,
                        "strategy": "search_fallback",
                        "search_query": result.get("search_query")
                    }
                )
            else:
                logger.warning(f"No tracks found for artist {artist_name} even with search fallback")
                return ToolResult.error_result(
                    f"No tracks found for artist {artist_name} using any method",
                    error_type="NoTracksFound"
                )

        except Exception as e:
            logger.error(f"Error in search fallback for artist {artist_id}: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed search fallback: {str(e)}",
                error_type=type(e).__name__
            )

    async def get_hybrid_tracks(
        self,
        access_token: str,
        artist_id: str,
        market: Optional[str] = None,
        max_popularity: int = 80,
        min_popularity: int = 20,
        target_count: int = 10,
        top_tracks_ratio: float = 0.4,
        prefetched_top_tracks: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get diverse tracks using hybrid strategy: top tracks + album deep cuts.

        This method combines:
        1. Filtered top tracks (excluding mega-hits with popularity > max_popularity)
        2. Album tracks for diversity (sampling from multiple albums)

        The ratio between top tracks and album tracks is controlled by top_tracks_ratio.

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: Optional ISO 3166-1 alpha-2 country code (None for global)
            max_popularity: Maximum popularity threshold (default: 80)
            min_popularity: Minimum popularity threshold (default: 20)
            target_count: Target number of tracks to return (default: 10)
            top_tracks_ratio: Ratio of top tracks vs album tracks (default: 0.4)
                            - 0.4 = 40% top tracks, 60% album tracks (discovery-focused)
                            - 0.7 = 70% top tracks, 30% album tracks (popular-focused)

        Returns:
            List of diverse track dictionaries
        """
        all_tracks = []
        track_ids_seen = set()

        # Calculate how many tracks to get from each source
        top_tracks_count = max(1, int(target_count * top_tracks_ratio))
        album_tracks_count = target_count - top_tracks_count

        # Step 1: Get top tracks (filtered)
        logger.info(
            f"Fetching top tracks for artist {artist_id} "
            f"(max_popularity: {max_popularity}, ratio: {top_tracks_ratio:.1%}, "
            f"target: {top_tracks_count} top + {album_tracks_count} album = {target_count} total)"
        )
        # Always use prefetched tracks (empty list if not available) to avoid individual API calls
        # that can cause rate limits when processing multiple artists in parallel
        top_tracks = prefetched_top_tracks if prefetched_top_tracks is not None else []
        if top_tracks:
            logger.debug(f"Using {len(top_tracks)} prefetched top tracks for artist {artist_id}")
        else:
            logger.debug(f"No prefetched top tracks for artist {artist_id}, will rely on album tracks")

        if top_tracks:
            filtered_top_tracks = [
                track for track in top_tracks
                if min_popularity <= track.get("popularity", 50) <= max_popularity
            ]
            logger.info(
                f"Filtered top tracks: {len(filtered_top_tracks)}/{len(top_tracks)} "
                f"within popularity range {min_popularity}-{max_popularity}"
            )

            for track in filtered_top_tracks[:top_tracks_count]:
                track_id = track.get("id")
                if track_id and track_id not in track_ids_seen:
                    all_tracks.append(track)
                    track_ids_seen.add(track_id)

        # Step 2: Get album tracks for diversity (if ratio allows)
        if album_tracks_count > 0:
            logger.info(f"Fetching albums for artist {artist_id}")
            # Add small delay before album fetch to avoid rate limits when processing multiple artists
            await asyncio.sleep(0.5)  # 500ms delay to space out album API calls
            albums = await get_artist_albums(
                make_request=self._make_request,
                access_token=access_token,
                artist_id=artist_id,
                market=market,
                limit=5  # Reduced from 10 to 5 albums to reduce API calls and avoid rate limits
            )

            if albums:
                logger.info(f"Found {len(albums)} albums, sampling tracks for diversity")
                # Sample tracks from albums
                album_tracks = await sample_album_tracks(
                    make_request=self._make_request,
                    validate_response=self._validate_response,
                    access_token=access_token,
                    albums=albums,
                    market=market,
                    max_tracks=album_tracks_count,
                    track_ids_seen=track_ids_seen,
                    min_popularity=min_popularity,
                    max_popularity=max_popularity
                )
                all_tracks.extend(album_tracks)

        # Deduplicate and limit
        unique_tracks = []
        final_ids_seen = set()
        for track in all_tracks:
            track_id = track.get("id")
            if track_id and track_id not in final_ids_seen:
                unique_tracks.append(track)
                final_ids_seen.add(track_id)
                if len(unique_tracks) >= target_count:
                    break

        # Count actual top vs album tracks
        actual_top_count = min(len(unique_tracks), top_tracks_count)
        actual_album_count = len(unique_tracks) - actual_top_count

        logger.info(
            f"Hybrid strategy returned {len(unique_tracks)} diverse tracks "
            f"(ratio: {top_tracks_ratio:.1%}, top: {actual_top_count}, album: {actual_album_count})"
        )

        return unique_tracks


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
