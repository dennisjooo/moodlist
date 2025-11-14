"""Rate limit error handling utilities.

This module provides utilities for handling HTTP 429 (rate limit) errors
with appropriate retry logic and backoff strategies.
"""

import asyncio
import structlog
from typing import Tuple, Optional, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .agent_tools import APIError

try:
    from .spotify.utils.rate_limiting import register_artist_top_tracks_retry_after
except ImportError:  # pragma: no cover - defensive in case spotify module missing
    register_artist_top_tracks_retry_after = None

logger = structlog.get_logger(__name__)


async def handle_rate_limit_error(
    e: httpx.HTTPStatusError,
    attempt: int,
    max_retries: int,
    tool_name: str
) -> Tuple[Optional["APIError"], bool]:
    """Handle HTTP 429 rate limit errors with appropriate retry logic.
    
    Args:
        e: The HTTPStatusError exception with status code 429
        attempt: Current retry attempt number (0-indexed)
        max_retries: Maximum number of retries allowed
        tool_name: Name of the tool making the request (for logging)
        
    Returns:
        Tuple of (APIError if should fail fast, should_continue_retrying)
        - If should_continue_retrying is True, the caller should retry
        - If APIError is not None, the caller should fail with that error
    """
    if e.response.status_code != 429:
        return None, False
    
    if attempt >= max_retries - 1:
        # No more retries left
        return None, False
    
    error_data = {"status_code": e.response.status_code, "error": str(e)}
    try:
        error_data.update(e.response.json())
    except (ValueError, AttributeError):
        # Response body wasn't JSON or doesn't have json() method
        pass
    
    retry_after = e.response.headers.get("Retry-After")
    if retry_after:
        wait_time = float(retry_after)
        # If retry-after is > 5 minutes (300s), fail fast instead of waiting
        if wait_time > 300:
            logger.error(
                f"Rate limit (429) with long retry-after ({wait_time:.0f}s) for {tool_name}. "
                "Failing immediately to avoid blocking workflow."
            )
            # Import here to avoid circular import
            from .agent_tools import APIError
            return APIError(
                f"Rate limited by API (retry after {wait_time:.0f}s)",
                response_data=error_data
            ), False
        else:
            # Use the retry-after value
            wait_time_to_use = wait_time
    else:
        # Aggressive exponential backoff: 2s, 8s, 32s
        wait_time_to_use = (2 ** (attempt + 1)) * 2.0
    
    if wait_time_to_use <= 300:  # Only retry if wait time is reasonable
        if (
            register_artist_top_tracks_retry_after
            and tool_name in {"get_artist_top_tracks", "batch_get_artist_top_tracks"}
        ):
            await register_artist_top_tracks_retry_after(wait_time_to_use)

        logger.warning(f"Rate limit (429) when calling {tool_name}, retrying in {wait_time_to_use}s...")
        await asyncio.sleep(wait_time_to_use)
        return None, True
    else:
        # Wait time is too long, fail fast
        # Import here to avoid circular import
        from .agent_tools import APIError
        return APIError(
            f"Rate limited by API (retry after {wait_time_to_use:.0f}s)",
            response_data=error_data
        ), False
