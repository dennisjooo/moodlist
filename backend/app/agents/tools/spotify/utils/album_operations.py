"""Album-related operations for Spotify API.

This module provides utilities for fetching and sampling tracks from albums,
separated from the main artist search tool for better modularity.
"""

import random
from typing import Any, Callable, Dict, List, Optional, Set

import structlog

from .batch_operations import batch_fetch_tracks, create_popularity_filter
from .params_utils import build_market_params

logger = structlog.get_logger(__name__)


async def get_artist_albums(
    make_request: Callable,
    access_token: str,
    artist_id: str,
    market: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get artist's albums.

    Args:
        make_request: Async function to make API requests
        access_token: Spotify access token
        artist_id: Spotify artist ID
        market: Optional ISO 3166-1 alpha-2 country code (None for global)
        limit: Maximum number of albums to return

    Returns:
        List of album dictionaries
    """
    try:
        params = build_market_params(
            market=market, limit=limit, include_groups="album,single"
        )

        response_data = await make_request(
            method="GET",
            endpoint=f"/artists/{artist_id}/albums",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if not response_data or "items" not in response_data:
            logger.warning(
                f"Invalid response structure for albums of artist {artist_id}"
            )
            return []

        albums = response_data.get("items", [])
        logger.info(f"Retrieved {len(albums)} albums for artist {artist_id}")
        return albums

    except Exception as e:
        logger.warning(f"Error fetching albums for artist {artist_id}: {e}")
        return []


async def sample_album_tracks(
    make_request: Callable,
    validate_response: Callable,
    access_token: str,
    albums: List[Dict[str, Any]],
    market: Optional[str],
    max_tracks: int,
    track_ids_seen: Set[str],
    min_popularity: int = 20,
    max_popularity: int = 80,
) -> List[Dict[str, Any]]:
    """Sample tracks from multiple albums for diversity.

    Args:
        make_request: Async function to make API requests
        validate_response: Function to validate API responses
        access_token: Spotify access token
        albums: List of album dictionaries
        market: Optional ISO 3166-1 alpha-2 country code (None for global)
        max_tracks: Maximum tracks to sample
        track_ids_seen: Set of track IDs already included
        min_popularity: Minimum popularity threshold
        max_popularity: Maximum popularity threshold

    Returns:
        List of sampled track dictionaries
    """
    # Prioritize albums (newer albums first, but with some randomness)
    albums_to_sample = albums.copy()
    random.shuffle(albums_to_sample)
    albums_to_sample = albums_to_sample[:5]  # Sample from up to 5 albums

    # Step 1: Collect track IDs from albums via batched /albums requests
    candidate_track_ids: List[str] = []
    tracks_per_album = max(1, max_tracks // max(1, len(albums_to_sample)))
    album_track_map: Dict[str, List[Dict[str, Any]]] = {}
    album_ids = [album.get("id") for album in albums_to_sample if album.get("id")]

    for i in range(
        0, len(album_ids), 20
    ):  # Spotify allows 20 album IDs per /albums call
        chunk = album_ids[i : i + 20]
        if not chunk:
            continue

        try:
            params = build_market_params(market=market, ids=",".join(chunk))
            response_data = await make_request(
                method="GET",
                endpoint="/albums",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if not validate_response(response_data, ["albums"]):
                continue

            for album_data in response_data.get("albums", []):
                album_id = album_data.get("id")
                if not album_id:
                    continue
                tracks_data = album_data.get("tracks", {})
                album_track_map[album_id] = tracks_data.get("items", []) or []

        except Exception as e:
            logger.warning(f"Error fetching album batch {chunk}: {e}")
            continue

    for album in albums_to_sample:
        album_id = album.get("id")
        if not album_id:
            continue
        album_tracks = album_track_map.get(album_id, [])
        if not album_tracks:
            continue

        # Sample random tracks from middle/end of album (avoid lead singles)
        if len(album_tracks) > 3:
            sample_pool = album_tracks[1:]
            sample_size = min(tracks_per_album, len(sample_pool))
            sampled = random.sample(sample_pool, sample_size) if sample_size > 0 else []
        else:
            sampled = album_tracks

        for track in sampled:
            track_id = track.get("id")
            if track_id and track_id not in track_ids_seen:
                candidate_track_ids.append(track_id)

    # Step 2: Batch fetch full track info for all candidates
    if not candidate_track_ids:
        return []

    # Create a wrapper function for making requests that matches batch_fetch_tracks API
    async def make_request_wrapper(
        endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Wrapper to adapt _make_request signature for batch_fetch_tracks."""
        response = await make_request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not validate_response(response, ["tracks"]):
            return {}
        return response

    # Use batch operations utility with popularity filter
    popularity_filter = create_popularity_filter(min_popularity, max_popularity)
    sampled_tracks = await batch_fetch_tracks(
        track_ids=candidate_track_ids,
        make_request=make_request_wrapper,
        access_token=access_token,
        market=market,
        track_ids_seen=track_ids_seen,
        filter_func=popularity_filter,
        max_results=max_tracks,
    )

    return sampled_tracks
