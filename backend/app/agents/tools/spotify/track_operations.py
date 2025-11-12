"""Track-related operations for Spotify API.

This module provides utilities for fetching track information,
separated from the main artist search tool for better modularity.
"""

import structlog
from typing import Dict, Any, Optional, Callable

from .track_parsing import parse_track_data
from .params_utils import build_market_params

logger = structlog.get_logger(__name__)


async def get_track_info(
    make_request: Callable,
    access_token: str,
    track_id: str,
    market: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get full track information including popularity.
    
    Args:
        make_request: Async function to make API requests
        access_token: Spotify access token
        track_id: Spotify track ID
        market: Optional ISO 3166-1 alpha-2 country code (None for global)
        
    Returns:
        Track dictionary or None if failed
    """
    try:
        params = build_market_params(market=market)
        
        response_data = await make_request(
            method="GET",
            endpoint=f"/tracks/{track_id}",
            params=params,
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


async def search_artist_tracks(
    make_request: Callable,
    validate_response: Callable,
    access_token: str,
    artist_id: str,
    artist_name: str,
    market: Optional[str] = None,
    limit: int = 20
) -> Optional[Dict[str, Any]]:
    """Search for artist tracks using the search API.
    
    This is a fallback strategy when the top-tracks endpoint fails.
    
    Args:
        make_request: Async function to make API requests
        validate_response: Function to validate API responses
        access_token: Spotify access token
        artist_id: Spotify artist ID
        artist_name: Artist name for search query
        market: Optional ISO 3166-1 alpha-2 country code (None for global)
        limit: Maximum number of tracks to return
        
    Returns:
        Dictionary with tracks and metadata, or None if failed
    """
    try:
        search_query = f"artist:{artist_name}"
        params = build_market_params(
            market=market,
            q=search_query,
            type="track",
            limit=limit
        )
        
        search_response = await make_request(
            method="GET",
            endpoint="/search",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if not validate_response(search_response, ["tracks"]):
            return None
        
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
                
                track_info = parse_track_data(track_data)
                tracks.append(track_info)
                
            except Exception as e:
                logger.warning(f"Failed to parse search track data: {track_data}, error: {e}")
                continue
        
        # Sort by popularity (most popular first) and take top 10
        tracks.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        tracks = tracks[:10]
        
        return {
            "tracks": tracks,
            "total_count": len(tracks),
            "artist_id": artist_id,
            "artist_name": artist_name,
            "search_query": search_query
        }
        
    except Exception as e:
        logger.error(f"Error searching for artist tracks: {str(e)}", exc_info=True)
        return None

