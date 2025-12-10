"""Whitelist checking utilities for Spotify dev mode."""

from typing import Optional

import structlog
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.exceptions import SpotifyAuthError
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


NOT_WHITELISTED_MESSAGE = (
    "NOT_WHITELISTED: Your Spotify account is not whitelisted for beta access. "
    "MoodList is currently in limited beta (25 users max). "
    "Please request access to be added to the whitelist."
)


def is_whitelist_error(error_msg: str) -> bool:
    """Check if an error message indicates a whitelist issue.

    Args:
        error_msg: Error message to check

    Returns:
        True if this is a whitelist error
    """
    if not settings.SPOTIFY_DEV_MODE:
        return False

    whitelist_indicators = ["403", "Insufficient permissions", "permissions"]
    error_lower = error_msg.lower()
    return any(indicator.lower() in error_lower for indicator in whitelist_indicators)


async def handle_whitelist_error(
    user_repo: UserRepository,
    access_token: str,
    refresh_token: str,
    token_expires_at,
    ip_address: Optional[str] = None,
) -> None:
    """Handle whitelist error by updating existing user status if found.

    Args:
        user_repo: User repository
        access_token: Access token from request
        refresh_token: Refresh token from request
        token_expires_at: Token expiration time
        ip_address: Optional IP address for logging

    Raises:
        SpotifyAuthError: Always raises NOT_WHITELISTED error
    """
    logger.error("User not whitelisted in Spotify dev mode", ip=ip_address)

    # Try to find and update existing user
    try:
        stmt = select(User).where(
            or_(User.access_token == access_token, User.refresh_token == refresh_token)
        )
        result = await user_repo.session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Update their whitelist status
            existing_user.is_spotify_whitelisted = False
            existing_user.access_token = access_token
            existing_user.refresh_token = refresh_token
            existing_user.token_expires_at = token_expires_at
            await user_repo.session.commit()

            logger.info(
                "Updated existing user whitelist status to False",
                user_id=existing_user.id,
                spotify_id=existing_user.spotify_id,
            )
        else:
            logger.warning(
                "Could not find existing user to update whitelist status - tokens may have rotated"
            )
    except Exception as db_error:
        logger.error(
            "Failed to update existing user whitelist status", error=str(db_error)
        )
        # Continue to raise the NOT_WHITELISTED error even if DB update fails

    # Always raise the whitelist error
    raise SpotifyAuthError(NOT_WHITELISTED_MESSAGE)
