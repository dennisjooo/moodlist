"""Spotify-specific rate limiting utilities.

This module provides rate limiting mechanisms for Spotify API endpoints
that require special handling to avoid hitting rate limits.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


# Global rate limiter for Spotify's /artists/{id}/top-tracks endpoint
# Shared across all tools to prevent hitting Spotify's rate limits
_artist_top_tracks_lock = asyncio.Lock()
_artist_top_tracks_last_request: Optional[datetime] = None
_artist_top_tracks_block_until: Optional[datetime] = None
_ARTIST_TOP_TRACKS_MIN_INTERVAL = 1.5  # 1.5 seconds between ANY top-tracks requests


async def wait_for_artist_top_tracks_rate_limit():
    """Global rate limiter for artist top tracks endpoint.

    This function ensures that requests to Spotify's /artists/{id}/top-tracks
    endpoint are spaced at least 1.5 seconds apart, regardless of which tool
    or service is making the request. This prevents hitting Spotify's rate limits
    when multiple components request top tracks concurrently.

    Usage:
        await wait_for_artist_top_tracks_rate_limit()
        # Now safe to make top-tracks API request
    """
    global _artist_top_tracks_last_request, _artist_top_tracks_block_until
    async with _artist_top_tracks_lock:
        if _artist_top_tracks_block_until is not None:
            now = datetime.now(timezone.utc)
            if now < _artist_top_tracks_block_until:
                wait_time = (_artist_top_tracks_block_until - now).total_seconds()
                logger.warning(
                    f"Backoff enforced for artist top-tracks endpoint, waiting {wait_time:.2f}s"
                )
                await asyncio.sleep(wait_time)
            _artist_top_tracks_block_until = None

        if _artist_top_tracks_last_request is not None:
            elapsed = (
                datetime.now(timezone.utc) - _artist_top_tracks_last_request
            ).total_seconds()
            if elapsed < _ARTIST_TOP_TRACKS_MIN_INTERVAL:
                wait_time = _ARTIST_TOP_TRACKS_MIN_INTERVAL - elapsed
                logger.debug(
                    f"Global rate limit: waiting {wait_time:.2f}s for artist top-tracks endpoint"
                )
                await asyncio.sleep(wait_time)
        _artist_top_tracks_last_request = datetime.now(timezone.utc)


async def register_artist_top_tracks_retry_after(wait_seconds: float):
    """Record a Retry-After signal so future requests honor the backoff."""
    if wait_seconds <= 0:
        return

    global _artist_top_tracks_block_until
    async with _artist_top_tracks_lock:
        block_until = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)
        if (
            _artist_top_tracks_block_until is None
            or block_until > _artist_top_tracks_block_until
        ):
            _artist_top_tracks_block_until = block_until
            logger.warning(
                f"Registered Retry-After backoff for artist top-tracks endpoint: {wait_seconds:.2f}s"
            )
