"""Spotify artist search and discovery tools."""

import structlog
from typing import List, Type, Dict, Any, Optional

from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


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
    market: str = Field(default="US", description="ISO 3166-1 alpha-2 country code")


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
        # Strategy 1: Try top-tracks endpoint with multiple markets
        result = await self._try_top_tracks_with_fallback_markets(access_token, artist_id, market)
        if result.success:
            return result

        # Strategy 2: If all markets failed, fallback to search by artist name
        logger.warning(f"All market attempts failed for artist {artist_id}, trying search fallback")
        return await self._try_search_fallback(access_token, artist_id, market)

    async def _try_top_tracks_with_fallback_markets(
        self,
        access_token: str,
        artist_id: str,
        market: str
    ) -> ToolResult:
        """Try getting top tracks using the top-tracks endpoint with fallback markets."""
        # Fallback markets to try if the primary market fails
        fallback_markets = ["US", "GB", "CA", "AU", "DE", "FR", "ES", "JP", "BR"]
        markets_to_try = [market] + [m for m in fallback_markets if m != market]

        last_error = None
        last_response_data = None

        for current_market in markets_to_try:
            try:
                logger.info(f"Getting top tracks for artist {artist_id} in market {current_market}")

                # Make API request
                response_data = await self._make_request(
                    method="GET",
                    endpoint=f"/artists/{artist_id}/top-tracks",
                    params={"market": current_market},
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                # Validate response structure
                if not self._validate_response(response_data, ["tracks"]):
                    last_error = "Invalid response structure from Spotify API"
                    last_response_data = response_data
                    continue

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

                # If we got tracks, return success
                if tracks:
                    logger.info(f"Successfully retrieved {len(tracks)} top tracks for artist {artist_id} using market {current_market}")
                    return ToolResult.success_result(
                        data={
                            "tracks": tracks,
                            "total_count": len(tracks),
                            "artist_id": artist_id
                        },
                        metadata={
                            "source": "spotify",
                            "api_endpoint": f"/artists/{artist_id}/top-tracks",
                            "market": current_market,
                            "original_market": market,
                            "fallback_used": current_market != market,
                            "strategy": "top_tracks"
                        }
                    )
                else:
                    logger.warning(f"No tracks found for artist {artist_id} in market {current_market}")
                    last_error = f"No tracks available for artist {artist_id} in market {current_market}"
                    continue

            except Exception as e:
                logger.warning(f"Error getting artist top tracks for market {current_market}: {str(e)}")
                last_error = str(e)
                continue

        # All markets failed
        logger.warning(f"All market attempts failed for artist {artist_id}: {last_error}")
        return ToolResult.error_result(
            f"Failed to get artist top tracks after trying {len(markets_to_try)} markets: {last_error}",
            error_type="AllMarketsFailed",
            api_response=last_response_data
        )

    async def _try_search_fallback(
        self,
        access_token: str,
        artist_id: str,
        market: str
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

            # Search for tracks by this artist
            search_query = f"artist:{artist_name}"
            search_response = await self._make_request(
                method="GET",
                endpoint="/search",
                params={
                    "q": search_query,
                    "type": "track",
                    "limit": 20,  # Get up to 20 tracks
                    "market": market
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if not self._validate_response(search_response, ["tracks"]):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify search API",
                    api_response=search_response
                )

            # Parse tracks from search results
            tracks = []
            tracks_data = search_response.get("tracks", {})
            items = tracks_data.get("items", [])

            for track_data in items:
                try:
                    # Only include tracks where this artist is the primary artist
                    track_artists = track_data.get("artists", [])
                    if not track_artists or track_artists[0].get("id") != artist_id:
                        continue

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
                    logger.warning(f"Failed to parse search track data: {track_data}, error: {e}")
                    continue

            # Sort by popularity (most popular first) and take top 10
            tracks.sort(key=lambda x: x.get("popularity", 0), reverse=True)
            tracks = tracks[:10]

            if tracks:
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
                        "search_query": search_query
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
        market: str = "US",
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
            market: ISO 3166-1 alpha-2 country code
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
        top_tracks: List[Dict[str, Any]] = []
        if prefetched_top_tracks is not None:
            top_tracks = prefetched_top_tracks
            logger.debug(f"Using prefetched top tracks for artist {artist_id} (count={len(top_tracks)})")
        else:
            top_tracks_result = await self._run(
                access_token=access_token,
                artist_id=artist_id,
                market=market
            )

            if top_tracks_result.success:
                top_tracks = top_tracks_result.data.get("tracks", [])
            else:
                logger.warning(
                    f"Failed to fetch top tracks inside hybrid strategy for artist {artist_id}: "
                    f"{top_tracks_result.error}"
                )

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
            albums = await self._get_artist_albums(
                access_token=access_token,
                artist_id=artist_id,
                market=market,
                limit=10  # Get recent 10 albums
            )

            if albums:
                logger.info(f"Found {len(albums)} albums, sampling tracks for diversity")
                # Sample tracks from albums
                album_tracks = await self._sample_album_tracks(
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

    async def _get_artist_albums(
        self,
        access_token: str,
        artist_id: str,
        market: str = "US",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get artist's albums.

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: ISO 3166-1 alpha-2 country code
            limit: Maximum number of albums to return

        Returns:
            List of album dictionaries
        """
        try:
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/artists/{artist_id}/albums",
                params={
                    "market": market,
                    "limit": limit,
                    "include_groups": "album,single"  # Include albums and singles
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if not self._validate_response(response_data, ["items"]):
                logger.warning(f"Invalid response structure for albums of artist {artist_id}")
                return []

            albums = response_data.get("items", [])
            logger.info(f"Retrieved {len(albums)} albums for artist {artist_id}")
            return albums

        except Exception as e:
            logger.warning(f"Error fetching albums for artist {artist_id}: {e}")
            return []

    async def _sample_album_tracks(
        self,
        access_token: str,
        albums: List[Dict[str, Any]],
        market: str,
        max_tracks: int,
        track_ids_seen: set,
        min_popularity: int = 20,
        max_popularity: int = 80
    ) -> List[Dict[str, Any]]:
        """Sample tracks from multiple albums for diversity.

        Args:
            access_token: Spotify access token
            albums: List of album dictionaries
            market: ISO 3166-1 alpha-2 country code
            max_tracks: Maximum tracks to sample
            track_ids_seen: Set of track IDs already included
            min_popularity: Minimum popularity threshold
            max_popularity: Maximum popularity threshold

        Returns:
            List of sampled track dictionaries
        """
        import random

        sampled_tracks = []
        tracks_per_album = max(1, max_tracks // min(len(albums), 5))  # Sample from up to 5 albums

        # Prioritize albums (newer albums first, but with some randomness)
        albums_to_sample = albums[:10]  # Consider recent 10 albums
        random.shuffle(albums_to_sample)  # Add randomness

        for album in albums_to_sample[:5]:  # Sample from up to 5 albums
            album_id = album.get("id")
            if not album_id:
                continue

            try:
                # Get tracks from this album
                response_data = await self._make_request(
                    method="GET",
                    endpoint=f"/albums/{album_id}/tracks",
                    params={"market": market, "limit": 50},
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if not self._validate_response(response_data, ["items"]):
                    continue

                album_tracks = response_data.get("items", [])

                # We need to get full track info (including popularity) via separate API call
                # For now, randomly sample tracks from the album
                if album_tracks:
                    # Sample random tracks from middle/end of album (avoid lead singles)
                    if len(album_tracks) > 3:
                        # Skip first track (usually the single) and sample from the rest
                        sample_pool = album_tracks[1:]
                        sampled = random.sample(sample_pool, min(tracks_per_album, len(sample_pool)))
                    else:
                        sampled = album_tracks

                    # Convert simplified tracks to full track format
                    for track in sampled:
                        track_id = track.get("id")
                        if track_id and track_id not in track_ids_seen:
                            # Fetch full track info to get popularity
                            full_track = await self._get_track_info(
                                access_token=access_token,
                                track_id=track_id,
                                market=market
                            )

                            if full_track:
                                popularity = full_track.get("popularity", 50)
                                # Apply popularity filter
                                if min_popularity <= popularity <= max_popularity:
                                    sampled_tracks.append(full_track)
                                    track_ids_seen.add(track_id)

                                    if len(sampled_tracks) >= max_tracks:
                                        return sampled_tracks

            except Exception as e:
                logger.warning(f"Error sampling tracks from album {album_id}: {e}")
                continue

        return sampled_tracks

    async def _get_track_info(
        self,
        access_token: str,
        track_id: str,
        market: str
    ) -> Optional[Dict[str, Any]]:
        """Get full track information including popularity.

        Args:
            access_token: Spotify access token
            track_id: Spotify track ID
            market: ISO 3166-1 alpha-2 country code

        Returns:
            Track dictionary or None if failed
        """
        try:
            response_data = await self._make_request(
                method="GET",
                endpoint=f"/tracks/{track_id}",
                params={"market": market},
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if not response_data.get("id"):
                return None

            return {
                "id": response_data.get("id"),
                "name": response_data.get("name"),
                "spotify_uri": response_data.get("uri"),
                "duration_ms": response_data.get("duration_ms"),
                "popularity": response_data.get("popularity", 50),
                "explicit": response_data.get("explicit", False),
                "preview_url": response_data.get("preview_url"),
                "track_number": response_data.get("track_number"),
                "artists": [
                    {
                        "id": artist.get("id"),
                        "name": artist.get("name"),
                        "uri": artist.get("uri")
                    }
                    for artist in response_data.get("artists", [])
                ],
                "album": {
                    "id": response_data.get("album", {}).get("id"),
                    "name": response_data.get("album", {}).get("name"),
                    "uri": response_data.get("album", {}).get("uri"),
                    "release_date": response_data.get("album", {}).get("release_date")
                } if response_data.get("album") else None
            }

        except Exception as e:
            logger.warning(f"Error fetching track info for {track_id}: {e}")
            return None


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
