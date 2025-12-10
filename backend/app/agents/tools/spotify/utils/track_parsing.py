"""Track parsing utilities for Spotify API responses.

This module provides utilities for parsing and formatting track data
from Spotify API responses into a consistent format.
"""

from typing import Any, Dict, List


def parse_track_data(track_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single track from Spotify API response.

    Args:
        track_data: Raw track data from Spotify API

    Returns:
        Formatted track dictionary with standardized fields
    """
    return {
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
                "uri": artist.get("uri"),
            }
            for artist in track_data.get("artists", [])
        ],
        "album": {
            "id": track_data.get("album", {}).get("id"),
            "name": track_data.get("album", {}).get("name"),
            "uri": track_data.get("album", {}).get("uri"),
            "release_date": track_data.get("album", {}).get("release_date"),
        }
        if track_data.get("album")
        else None,
    }


def parse_tracks_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse multiple tracks from Spotify API response.

    Args:
        response_data: Response data containing tracks array

    Returns:
        List of parsed track dictionaries
    """
    tracks = []
    for track_data in response_data.get("tracks", []):
        try:
            track_info = parse_track_data(track_data)
            tracks.append(track_info)
        except Exception:
            # Skip tracks that fail to parse
            continue
    return tracks


def parse_tracks_batch(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse tracks from batch API response (e.g., /tracks endpoint with multiple IDs).

    Args:
        response_data: Response data containing tracks array (may include null entries)

    Returns:
        List of parsed track dictionaries (null entries filtered out)
    """
    tracks = []
    for track_data in response_data.get("tracks", []):
        if not track_data:  # Skip null entries
            continue
        try:
            track_info = parse_track_data(track_data)
            tracks.append(track_info)
        except Exception:
            # Skip tracks that fail to parse
            continue
    return tracks
