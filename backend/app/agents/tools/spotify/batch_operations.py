"""Batch operations utilities for Spotify API.

This module provides utilities for batch fetching and processing
Spotify API data to reduce API calls and respect rate limits.
"""

import structlog
from typing import List, Dict, Any, Set, Callable, Awaitable

from .track_parsing import parse_track_data

logger = structlog.get_logger(__name__)

# Spotify API batch limit for tracks endpoint
SPOTIFY_BATCH_LIMIT = 50


async def batch_fetch_tracks(
    track_ids: List[str],
    make_request: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    access_token: str,
    market: str,
    track_ids_seen: Set[str],
    filter_func: Callable[[Dict[str, Any]], bool] = None,
    max_results: int = None
) -> List[Dict[str, Any]]:
    """Batch fetch full track information for multiple track IDs.
    
    Fetches tracks in batches of 50 (Spotify API limit) and applies
    optional filtering and popularity checks.
    
    Args:
        track_ids: List of Spotify track IDs to fetch
        make_request: Async function to make API requests
                     Signature: (endpoint: str, params: Dict) -> Dict
        access_token: Spotify access token
        market: ISO 3166-1 alpha-2 country code
        track_ids_seen: Set of track IDs already processed (will be updated)
        filter_func: Optional function to filter tracks (returns True to include)
        max_results: Maximum number of tracks to return (None for all)
        
    Returns:
        List of parsed track dictionaries
    """
    if not track_ids:
        return []
    
    results = []
    
    # Process in batches of 50 (Spotify API limit)
    for i in range(0, len(track_ids), SPOTIFY_BATCH_LIMIT):
        batch_ids = track_ids[i:i + SPOTIFY_BATCH_LIMIT]
        
        try:
            response_data = await make_request(
                "/tracks",
                {
                    "ids": ",".join(batch_ids),
                    "market": market
                }
            )
            
            if not response_data or "tracks" not in response_data:
                continue
            
            for track_data in response_data.get("tracks", []):
                if not track_data:  # Skip null entries
                    continue
                
                track_id = track_data.get("id")
                if not track_id or track_id in track_ids_seen:
                    continue
                
                # Apply optional filter function
                if filter_func and not filter_func(track_data):
                    continue
                
                # Parse track data using standard parser
                try:
                    parsed_track = parse_track_data(track_data)
                    results.append(parsed_track)
                    track_ids_seen.add(track_id)
                    
                    if max_results and len(results) >= max_results:
                        return results
                except Exception as e:
                    logger.warning(f"Failed to parse track {track_id}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Error batch fetching track info: {e}")
            continue
    
    return results


def create_popularity_filter(min_popularity: int, max_popularity: int) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter function for track popularity.
    
    Args:
        min_popularity: Minimum popularity score (0-100)
        max_popularity: Maximum popularity score (0-100)
        
    Returns:
        Filter function that returns True if track popularity is within range
    """
    def filter_func(track_data: Dict[str, Any]) -> bool:
        popularity = track_data.get("popularity", 50)
        return min_popularity <= popularity <= max_popularity
    
    return filter_func

