"""Utilities for building Spotify API request parameters.

This module provides helper functions for building request parameters
consistently across the codebase, especially for optional parameters like market.
"""

from typing import Any, Dict, Optional


def build_market_params(
    market: Optional[str] = None, **additional_params
) -> Dict[str, Any]:
    """Build request params with optional market parameter.

    This helper ensures consistent handling of the optional market parameter:
    - If market is None, it's excluded from params (uses Spotify's global default)
    - If market is provided, it's included in params

    Args:
        market: Optional ISO 3166-1 alpha-2 country code (None for global)
        **additional_params: Additional parameters to include in the request

    Returns:
        Dictionary of request parameters

    Examples:
        >>> build_market_params(market="US", limit=10)
        {"market": "US", "limit": 10}

        >>> build_market_params(market=None, limit=10)
        {"limit": 10}
    """
    params = dict(additional_params)
    if market is not None:
        params["market"] = market
    return params


def normalize_market_for_cache(market: Optional[str]) -> str:
    """Normalize market parameter for cache key generation.

    Converts None to "global" for consistent cache keys, since we want to cache
    global market responses separately from country-specific responses.

    Args:
        market: Optional ISO 3166-1 alpha-2 country code (None for global)

    Returns:
        Market code or "global" if None

    Examples:
        >>> normalize_market_for_cache("US")
        "US"

        >>> normalize_market_for_cache(None)
        "global"
    """
    return market if market is not None else "global"


def get_market_label(market: Optional[str]) -> str:
    """Get a human-readable label for the market parameter.

    Useful for logging and debugging.

    Args:
        market: Optional ISO 3166-1 alpha-2 country code (None for global)

    Returns:
        Market code or "global" if None

    Examples:
        >>> get_market_label("US")
        "US"

        >>> get_market_label(None)
        "global"
    """
    return market if market is not None else "global"
