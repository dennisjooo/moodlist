"""Utilities for deduplicating track recommendations."""

from typing import Callable, Iterable, List, Tuple

from ...states.agent_state import TrackRecommendation

# Type alias for duplicate callback signature
DuplicateCallback = Callable[[TrackRecommendation], None]


def _normalize_title_artist_key(track_name: str, artists: List[str]) -> str:
    """Create a normalized key for title-artist deduplication.

    Args:
        track_name: The track name
        artists: List of artist names

    Returns:
        Normalized key combining title and artists
    """
    # Normalize track name
    normalized_title = track_name.lower().strip()

    # Normalize and sort artists for consistent comparison
    normalized_artists = sorted(artist.lower().strip() for artist in artists)

    # Combine with separator that's unlikely to appear in names
    return f"{normalized_title}|{'|'.join(normalized_artists)}"


def deduplicate_track_recommendations(
    recommendations: Iterable[TrackRecommendation],
    *,
    on_duplicate: DuplicateCallback | None = None,
) -> Tuple[List[TrackRecommendation], int]:
    """Remove duplicate track recommendations while preserving order.

    Duplicates are detected by matching track IDs, Spotify URIs, or
    track title + artist combinations (case-insensitive).

    Args:
        recommendations: Iterable of track recommendations to inspect.
        on_duplicate: Optional callback executed for each duplicate encountered.

    Returns:
        A tuple of (unique recommendations, duplicate count).
    """
    seen_track_ids = set()
    seen_spotify_uris = set()
    seen_title_artist_keys = set()
    unique_recommendations: List[TrackRecommendation] = []
    duplicates_removed = 0

    for rec in recommendations:
        spotify_uri = rec.spotify_uri
        title_artist_key = _normalize_title_artist_key(rec.track_name, rec.artists)

        is_duplicate = (
            rec.track_id in seen_track_ids or
            (spotify_uri and spotify_uri in seen_spotify_uris) or
            title_artist_key in seen_title_artist_keys
        )

        if is_duplicate:
            duplicates_removed += 1
            if on_duplicate:
                on_duplicate(rec)
            continue

        seen_track_ids.add(rec.track_id)
        if spotify_uri:
            seen_spotify_uris.add(spotify_uri)
        seen_title_artist_keys.add(title_artist_key)
        unique_recommendations.append(rec)

    return unique_recommendations, duplicates_removed
