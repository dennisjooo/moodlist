import hashlib
import structlog
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import verify_token
from app.core.exceptions import (
    UnauthorizedException,
    InternalServerError,
    SpotifyAuthError,
    RateLimitException,
)
from app.clients import SpotifyAPIClient
from app.models.session import Session
from app.models.user import User
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.services.quota_service import QuotaService
from app.dependencies import (
    get_user_repository,
    get_session_repository,
    get_quota_service,
)

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


def _hash_token_for_logging(token: str) -> str:
    """Hash a token for secure logging.

    Args:
        token: The token to hash

    Returns:
        First 16 characters of SHA256 hash for logging purposes
    """
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise UnauthorizedException("Authentication credentials not provided")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    user = await user_repo.get_active_user_by_spotify_id(payload["sub"])

    if not user:
        raise UnauthorizedException("User not found or inactive")

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None

    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            return None

        return await user_repo.get_active_user_by_spotify_id(payload["sub"])
    except (ValueError, KeyError, jwt.JWTError) as e:
        # Expected JWT validation failures - these are normal
        logger.debug("Token validation failed", error=str(e))
        return None
    except Exception as e:
        # Unexpected errors (e.g., database failures) should be logged and re-raised
        logger.error(
            "Unexpected error in get_current_user_optional", error=str(e), exc_info=True
        )
        raise


async def get_current_session(
    request: Request, session_repo: SessionRepository = Depends(get_session_repository)
) -> Optional[Session]:
    """Get current session from session token."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        logger.debug("No session token found in cookies")
        return None

    logger.debug(
        "Looking up session", token_hash=_hash_token_for_logging(session_token)
    )

    session = await session_repo.get_valid_session_by_token(session_token)

    if session:
        logger.debug(
            "Session found",
            session_id=session.id,
            user_id=session.user_id,
            expires_at=session.expires_at,
        )
    else:
        logger.debug(
            "No valid session found",
            token_hash=_hash_token_for_logging(session_token)
            if session_token
            else "None",
        )

    return session


async def require_auth(
    user: Optional[User] = Depends(get_current_user_optional),
    session: Optional[Session] = Depends(get_current_session),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Require authentication via either JWT token or session."""
    logger.debug("require_auth called", has_user=bool(user), has_session=bool(session))

    if not user and not session:
        logger.debug("No user or session found")
        raise UnauthorizedException("Authentication required")

    # If we have a session but no user, get user from session
    if not user and session:
        logger.debug(
            "Getting user from session", session_id=session.id, user_id=session.user_id
        )
        user = await user_repo.get_active_user_by_id(session.user_id)
        logger.debug("User from session", found=bool(user))

    if not user:
        logger.debug("No user found after session lookup")
        raise UnauthorizedException("User not found or inactive")

    return user


async def refresh_spotify_token_if_expired(user: User, db: AsyncSession) -> User:
    """Check if Spotify token is expired and refresh if needed.

    Args:
        user: User object with token information
        user_repo: User repository for database operations

    Returns:
        User object with refreshed token if needed

    Raises:
        HTTPException: If token refresh fails
    """
    # Check if token is expired or will expire in the next 5 minutes
    now = datetime.now(timezone.utc)

    # Validate token expiration exists
    token_expires_at = user.token_expires_at
    if not token_expires_at:
        logger.error("User has no token expiration time", user_id=user.id)
        raise SpotifyAuthError("Invalid token state. Please log in again.")

    # Handle both timezone-aware and naive datetimes
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

    # Add 5 minute buffer to refresh before actual expiration
    if token_expires_at > now:
        # Token is still valid
        logger.debug(
            "Spotify token still valid", user_id=user.id, expires_at=token_expires_at
        )
        return user

    logger.info(
        "Spotify token expired, refreshing",
        user_id=user.id,
        expired_at=token_expires_at,
    )

    # Refresh the token using SpotifyAPIClient
    spotify_client = SpotifyAPIClient()
    try:
        token_data = await spotify_client.refresh_token(user.refresh_token)

        # Update expiration time
        expires_in = token_data.get("expires_in", 3600)
        new_token_expires_at = datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(seconds=expires_in)

        user_repo = UserRepository(db)
        updated_user = await user_repo.update_tokens_and_commit(
            user_id=user.id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", user.refresh_token),
            token_expires_at=new_token_expires_at,
        )

        logger.info(
            "Spotify token refreshed successfully",
            user_id=updated_user.id,
            new_expires_at=updated_user.token_expires_at,
        )

        return updated_user

    except SpotifyAuthError as e:
        logger.error("Failed to refresh Spotify token", user_id=user.id, error=str(e))
        raise SpotifyAuthError("Failed to refresh Spotify token. Please log in again.")
    except Exception as e:
        logger.error(
            "Unexpected error refreshing Spotify token",
            user_id=user.id,
            error=str(e),
            exc_info=True,
        )
        raise InternalServerError("Failed to refresh token. Please try again later.")


async def check_playlist_creation_rate_limit(
    current_user: User = Depends(require_auth),
    quota_service: QuotaService = Depends(get_quota_service),
) -> None:
    """Check if user has exceeded daily playlist creation limit.

    Args:
        current_user: Authenticated user (injected via dependency)
        quota_service: Cached quota service

    Raises:
        RateLimitException: If user has exceeded daily limit
    """
    if settings.APP_ENV == "development":
        return

    count = await quota_service.get_daily_usage(current_user.id)

    if count >= settings.DAILY_PLAYLIST_CREATION_LIMIT:
        raise RateLimitException(
            detail=f"You've created {settings.DAILY_PLAYLIST_CREATION_LIMIT} playlists today! Come back tomorrow for more musical adventures.",
            retry_after=86400,  # 24 hours in seconds
        )
