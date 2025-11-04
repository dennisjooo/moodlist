"""Utilities for deduplicating track recommendations."""

from typing import Callable, Iterable, List, Tuple

from ...states.agent_state import TrackRecommendation

# Type alias for duplicate callback signature
DuplicateCallback = Callable[[TrackRecommendation], None]


def deduplicate_track_recommendations(
    recommendations: Iterable[TrackRecommendation],
    *,
    on_duplicate: DuplicateCallback | None = None
) -> Tuple[List[TrackRecommendation], int]:
    """Remove duplicate track recommendations while preserving order.

    Duplicates are detected by either matching track IDs or Spotify URIs.

    Args:
        recommendations: Iterable of track recommendations to inspect.
        on_duplicate: Optional callback executed for each duplicate encountered.

    Returns:
        A tuple of (unique recommendations, duplicate count).
    """
    seen_track_ids = set()
    seen_spotify_uris = set()
    unique_recommendations: List[TrackRecommendation] = []
    duplicates_removed = 0

    for rec in recommendations:
        spotify_uri = rec.spotify_uri
        is_duplicate = (
            rec.track_id in seen_track_ids
            or (spotify_uri and spotify_uri in seen_spotify_uris)
        )

        if is_duplicate:
            duplicates_removed += 1
            if on_duplicate:
                on_duplicate(rec)
            continue

        seen_track_ids.add(rec.track_id)
        if spotify_uri:
            seen_spotify_uris.add(spotify_uri)
        unique_recommendations.append(rec)

    return unique_recommendations, duplicates_removed
