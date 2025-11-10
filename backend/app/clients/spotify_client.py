"""Centralized Spotify API client with built-in error handling and retry logic."""

import asyncio
from typing import Dict, Any, Optional
import httpx
import structlog

from app.core.config import settings
from app.agents.core.cache import cache_manager
from app.core.constants import SpotifyEndpoints, HTTPTimeouts
from app.core.exceptions import (
    SpotifyAuthError,
    SpotifyRateLimitError,
    SpotifyServerError,
    SpotifyConnectionError,
    SpotifyAPIException
)

logger = structlog.get_logger(__name__)


class SpotifyAPIClient:
    """Centralized Spotify API client with built-in error handling and retry logic."""
    
    def __init__(self, timeout: int = HTTPTimeouts.SPOTIFY_API, max_retries: int = 3):
        """Initialize the Spotify API client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger
    
    async def get_user_profile(self, access_token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user profile from Spotify.

        Args:
            access_token: Spotify access token
            user_id: Optional user ID for caching (Spotify user ID)

        Returns:
            User profile data

        Raises:
            SpotifyAuthError: If token is invalid or expired
            SpotifyAPIException: For other API errors
        """
        # Try to get from cache first if user_id is provided
        if user_id:
            cached_profile = await cache_manager.get_user_profile(user_id)
            if cached_profile is not None:
                self.logger.debug(f"Cache hit for user profile {user_id}")
                return cached_profile

        # Cache miss or no user_id provided - fetch from API
        if user_id:
            self.logger.debug(f"Cache miss for user profile {user_id}, fetching from API")
        else:
            self.logger.debug("Fetching user profile from API (no user_id for caching)")

        profile_data = await self._get(SpotifyEndpoints.USER_PROFILE, access_token)

        # Cache the result if user_id is provided
        if user_id:
            await cache_manager.set_user_profile(user_id, profile_data)

        return profile_data
    
    async def get_user_top_tracks(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term",
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's top tracks.
        
        Args:
            access_token: Spotify access token
            limit: Number of tracks to return (max 50)
            time_range: Time range (short_term, medium_term, long_term)
            offset: Offset for pagination
            
        Returns:
            Top tracks data
        """
        params = {
            "limit": limit,
            "time_range": time_range,
            "offset": offset
        }
        return await self._get(SpotifyEndpoints.USER_TOP_TRACKS, access_token, params=params)
    
    async def get_user_top_artists(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term",
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's top artists.
        
        Args:
            access_token: Spotify access token
            limit: Number of artists to return (max 50)
            time_range: Time range (short_term, medium_term, long_term)
            offset: Offset for pagination
            
        Returns:
            Top artists data
        """
        params = {
            "limit": limit,
            "time_range": time_range,
            "offset": offset
        }
        return await self._get(SpotifyEndpoints.USER_TOP_ARTISTS, access_token, params=params)
    
    async def get_user_playlists(
        self,
        access_token: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's playlists.
        
        Args:
            access_token: Spotify access token
            limit: Number of playlists to return (max 50)
            offset: Offset for pagination
            
        Returns:
            User playlists data
        """
        params = {"limit": limit, "offset": offset}
        return await self._get(SpotifyEndpoints.USER_PLAYLISTS, access_token, params=params)
    
    async def search_tracks(
        self,
        access_token: str,
        query: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for tracks.
        
        Args:
            access_token: Spotify access token
            query: Search query
            limit: Number of results to return (max 50)
            
        Returns:
            Search results
        """
        params = {
            "q": query,
            "type": "track",
            "limit": limit
        }
        return await self._get(SpotifyEndpoints.SEARCH, access_token, params=params)
    
    async def create_playlist(
        self,
        access_token: str,
        user_id: str,
        name: str,
        description: str = "",
        public: bool = True
    ) -> Dict[str, Any]:
        """Create a new playlist.
        
        Args:
            access_token: Spotify access token
            user_id: Spotify user ID
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public
            
        Returns:
            Created playlist data
        """
        json_data = {
            "name": name,
            "description": description,
            "public": public
        }
        return await self._post(
            f"/users/{user_id}/playlists",
            access_token,
            json=json_data
        )
    
    async def add_tracks_to_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add tracks to a playlist.
        
        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            track_uris: List of track URIs to add
            position: Position to insert tracks (optional)
            
        Returns:
            Response data
        """
        json_data = {"uris": track_uris}
        if position is not None:
            json_data["position"] = position
        
        return await self._post(
            f"/playlists/{playlist_id}/tracks",
            access_token,
            json=json_data
        )
    
    async def remove_tracks_from_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: list[str]
    ) -> Dict[str, Any]:
        """Remove tracks from a playlist.
        
        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            track_uris: List of track URIs to remove
            
        Returns:
            Response data
        """
        json_data = {"tracks": [{"uri": uri} for uri in track_uris]}
        return await self._delete(
            f"/playlists/{playlist_id}/tracks",
            access_token,
            json=json_data
        )
    
    async def reorder_playlist_tracks(
        self,
        access_token: str,
        playlist_id: str,
        range_start: int,
        insert_before: int,
        range_length: int = 1
    ) -> Dict[str, Any]:
        """Reorder tracks in a playlist.
        
        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            range_start: Position of first track to move
            insert_before: Position to insert tracks
            range_length: Number of tracks to move
            
        Returns:
            Response data
        """
        json_data = {
            "range_start": range_start,
            "insert_before": insert_before,
            "range_length": range_length
        }
        return await self._put(
            f"/playlists/{playlist_id}/tracks",
            access_token,
            json=json_data
        )
    
    async def get_track(
        self,
        access_token: str,
        track_id: str
    ) -> Dict[str, Any]:
        """Get track details.

        Args:
            access_token: Spotify access token
            track_id: Spotify track ID

        Returns:
            Track details
        """
        # Try to get from cache first
        cached_track = await cache_manager.get_track_details(track_id)
        if cached_track is not None:
            self.logger.debug(f"Cache hit for track {track_id}")
            return cached_track

        # Cache miss - fetch from API
        self.logger.debug(f"Cache miss for track {track_id}, fetching from API")
        track_data = await self._get(f"/tracks/{track_id}", access_token)

        # Cache the result
        await cache_manager.set_track_details(track_id, track_data)

        return track_data
    
    async def get_playlist_tracks(
        self,
        access_token: str,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get tracks from a playlist.
        
        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            limit: Number of tracks to return (max 100)
            offset: Offset for pagination
            
        Returns:
            Playlist tracks data
        """
        params = {"limit": limit, "offset": offset}
        return await self._get(f"/playlists/{playlist_id}/tracks", access_token, params=params)
    
    async def get_playlist(
        self,
        access_token: str,
        playlist_id: str
    ) -> Dict[str, Any]:
        """Get playlist details.
        
        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            
        Returns:
            Playlist details including snapshot_id
        """
        return await self._get(f"/playlists/{playlist_id}", access_token)
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Spotify access token.
        
        Args:
            refresh_token: Spotify refresh token
            
        Returns:
            New token data
            
        Raises:
            SpotifyAuthError: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "client_secret": settings.SPOTIFY_CLIENT_SECRET
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(SpotifyEndpoints.TOKEN_URL, data=data)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Token refresh failed",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise SpotifyAuthError("Failed to refresh Spotify token")
        except Exception as e:
            self.logger.error("Unexpected error during token refresh", error=str(e))
            raise SpotifyConnectionError(f"Failed to refresh token: {str(e)}")
    
    # Private methods for HTTP operations
    
    async def _get(
        self,
        endpoint: str,
        access_token: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make GET request to Spotify API."""
        return await self._request("GET", endpoint, access_token, params=params)
    
    async def _post(
        self,
        endpoint: str,
        access_token: str,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make POST request to Spotify API."""
        return await self._request("POST", endpoint, access_token, json=json)
    
    async def _put(
        self,
        endpoint: str,
        access_token: str,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make PUT request to Spotify API."""
        return await self._request("PUT", endpoint, access_token, json=json)
    
    async def _delete(
        self,
        endpoint: str,
        access_token: str,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make DELETE request to Spotify API."""
        return await self._request("DELETE", endpoint, access_token, json=json)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (with leading slash)
            access_token: Spotify access token
            **kwargs: Additional request parameters
            
        Returns:
            Response JSON data
            
        Raises:
            SpotifyAuthError: For authentication errors
            SpotifyRateLimitError: For rate limit errors
            SpotifyServerError: For server errors
            SpotifyConnectionError: For connection errors
            SpotifyAPIException: For other API errors
        """
        url = f"{SpotifyEndpoints.API_BASE}{endpoint}"
        headers = self._build_headers(access_token)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        **kwargs
                    )
                    response.raise_for_status()
                    
                    self.logger.debug(
                        "Spotify API request successful",
                        method=method,
                        endpoint=endpoint,
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                # Get response body for better error messages
                try:
                    error_body = e.response.json()
                except:
                    error_body = e.response.text
                
                self.logger.warning(
                    "Spotify API HTTP error",
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error_body=error_body
                )
                
                # Handle specific status codes
                if status_code == 401:
                    raise SpotifyAuthError("Invalid or expired token")
                elif status_code == 403:
                    error_msg = "Insufficient permissions - token may be missing required scopes. Please log out and log back in."
                    self.logger.error(
                        "Spotify 403 error - likely missing scopes",
                        endpoint=endpoint,
                        error_body=error_body,
                        hint="User needs to re-authenticate to get new token with correct scopes"
                    )
                    raise SpotifyAuthError(error_msg)
                elif status_code == 429:
                    # Rate limited - wait and retry
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        self.logger.info(
                            "Rate limited, waiting before retry",
                            wait_time=wait_time,
                            attempt=attempt + 1
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise SpotifyRateLimitError("Rate limit exceeded")
                elif status_code >= 500:
                    # Server error - retry
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        self.logger.info(
                            "Server error, retrying",
                            wait_time=wait_time,
                            attempt=attempt + 1
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise SpotifyServerError("Spotify server error")
                else:
                    # Other client errors - don't retry
                    raise SpotifyAPIException(
                        f"Spotify API error: {status_code}",
                        status_code=status_code
                    )
                    
            except httpx.RequestError as e:
                self.logger.error(
                    "Spotify API request error",
                    method=method,
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(
                        "Connection error, retrying",
                        wait_time=wait_time,
                        attempt=attempt + 1
                    )
                    await asyncio.sleep(wait_time)
                    continue
                    
                raise SpotifyConnectionError(f"Failed to connect to Spotify: {str(e)}")
        
        # Max retries exceeded
        raise SpotifyAPIException("Max retries exceeded")
    
    def _build_headers(self, access_token: str) -> Dict[str, str]:
        """Build request headers.
        
        Args:
            access_token: Spotify access token
            
        Returns:
            Headers dictionary
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
