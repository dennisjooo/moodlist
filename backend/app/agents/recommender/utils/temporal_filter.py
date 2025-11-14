"""Temporal filtering utilities for track recommendations."""

import structlog
from typing import Any, Dict, Optional, Tuple

logger = structlog.get_logger(__name__)


def check_temporal_match(
    track: Dict[str, Any],
    temporal_context: Optional[Dict[str, Any]]
) -> Tuple[bool, Optional[str]]:
    """Check if a track matches temporal filtering requirements.

    Args:
        track: Track dictionary from Spotify (should have album.release_date)
        temporal_context: Temporal context from mood analysis

    Returns:
        Tuple of (is_match, reason) where:
        - is_match: True if track matches temporal requirements or no constraint exists
        - reason: None if is_match=True, otherwise a string explaining why it was filtered
    """
    # If no temporal context or not temporal, allow all tracks
    if not temporal_context or not temporal_context.get('is_temporal'):
        return (True, None)

    # Extract year range
    year_range = temporal_context.get('year_range')
    if not year_range or len(year_range) != 2:
        return (True, None)

    min_year, max_year = year_range

    # Get release date from track
    album = track.get('album', {})
    release_date = album.get('release_date', '')

    if not release_date:
        # No release date - allow it (might be incomplete data)
        logger.debug(f"Track '{track.get('name')}' has no release_date, allowing")
        return (True, None)

    # Parse year from release_date (formats: YYYY, YYYY-MM-DD, YYYY-MM)
    try:
        release_year = int(release_date.split('-')[0])
    except (ValueError, IndexError):
        logger.debug(f"Could not parse release_date '{release_date}', allowing")
        return (True, None)

    # Add tolerance window for softer temporal matching
    # If temporal context is just from artist mentions (not explicit decade),
    # allow ±5 years of flexibility to avoid filtering out great matches
    is_strict_temporal = temporal_context.get('decade') or temporal_context.get('era')
    tolerance = 0 if is_strict_temporal else 5

    # Check if within range (with tolerance)
    if (min_year - tolerance) <= release_year <= (max_year + tolerance):
        return (True, None)
    else:
        decade = temporal_context.get('decade', f'{min_year}-{max_year}')
        reason = (
            f"Released in {release_year}, outside {decade} requirement "
            f"({min_year}-{max_year})"
        )
        return (False, reason)
