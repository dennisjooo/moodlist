import structlog

from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer

from app.core.constants import SessionConstants
from app.core.exceptions import UnauthorizedException, InternalServerError
from app.models.user import User
from app.auth.security import create_access_token, create_refresh_token, verify_token
from app.auth.dependencies import require_auth
from app.auth.cookie_utils import set_session_cookie, delete_session_cookie
from app.auth.schemas import (
    UserCreate,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    AuthResponse,
)
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.playlist_repository import PlaylistRepository
from app.services.quota_service import QuotaService
from app.services.auth_service import AuthService
from app.dependencies import (
    get_user_repository,
    get_session_repository,
    get_playlist_repository,
    get_quota_service,
    get_auth_service,
)
from app.agents.core.cache import cache_manager
from app.core.limiter import limiter

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    user_data: UserCreate,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login/Register a new user by fetching profile from Spotify.

    Rate limit: 10 requests per minute per IP address.
    """
    # Delegate to auth service
    user, session_token, tokens = await auth_service.login_user(
        access_token=user_data.access_token,
        refresh_token=user_data.refresh_token,
        token_expires_at=user_data.token_expires_at,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )

    # Set session cookie using utility (pass origin for localhost detection)
    origin = request.headers.get("origin")
    set_session_cookie(response, session_token, origin)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=3600,
        user=UserResponse.from_orm(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Refresh access token using refresh token.

    Rate limit: 20 requests per minute per IP address.
    """
    logger.info("Token refresh attempt")

    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token, "refresh")
    if not payload:
        raise UnauthorizedException("Invalid refresh token")

    # Get user
    user = await user_repo.get_active_user_by_spotify_id(payload["sub"])

    if not user:
        raise UnauthorizedException("User not found")

    # Create new tokens
    token_data = {"sub": user.spotify_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info("Token refresh successful", user_id=user.id, spotify_id=user.spotify_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=UserResponse.from_orm(user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    session_repo: SessionRepository = Depends(get_session_repository),
    current_user: Optional[User] = Depends(require_auth),
):
    """Logout user and clear session."""
    # Clear session cookie using utility (pass origin for localhost detection)
    origin = request.headers.get("origin")
    delete_session_cookie(response, origin)

    # Delete session from database if user is authenticated
    if current_user:
        session_token = request.cookies.get(SessionConstants.COOKIE_NAME)
        if session_token:
            # Clear auth verification cache
            cache_key = f"auth_verify:{session_token}"
            await cache_manager.cache.delete(cache_key)

            await session_repo.delete_by_token(session_token)

        logger.info(
            "Logout successful",
            user_id=current_user.id,
            spotify_id=current_user.spotify_id,
        )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information."""
    if not current_user:
        raise UnauthorizedException("Not authenticated")

    return UserResponse.from_orm(current_user)


@router.get("/verify", response_model=AuthResponse)
async def verify_auth(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Verify authentication status with optimized session-based auth and caching.

    Performance optimization: Single database query with join instead of multiple lookups,
    plus server-side caching to reduce database load.
    Before: 2-3 queries (session lookup + user lookup)
    After: 1 query with eager loading + 5-minute cache
    """
    session_token = request.cookies.get(SessionConstants.COOKIE_NAME)
    return await auth_service.verify_auth(session_token)


@router.get("/dashboard")
async def get_user_dashboard(
    current_user: User = Depends(require_auth),
    playlist_repo: PlaylistRepository = Depends(get_playlist_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    """Get comprehensive dashboard data for user including analytics and insights.

    Args:
        current_user: Authenticated user
        playlist_repo: Playlist repository
        session_repo: Session repository

    Returns:
        Dashboard data with stats, recent activity, mood distribution, and insights
    """
    try:
        # Get basic stats
        playlist_stats = await playlist_repo.get_user_playlist_stats(current_user.id)
        total_sessions = await session_repo.get_session_count(
            user_id=current_user.id, active_only=False
        )
        active_sessions = await session_repo.get_session_count(
            user_id=current_user.id, active_only=True
        )

        # Get recent playlists for activity timeline and mood analysis
        recent_playlists_data = await playlist_repo.get_user_recent_playlists(
            user_id=current_user.id, limit=10
        )

        # Get mood distribution and audio features analysis
        dashboard_analytics = await playlist_repo.get_user_dashboard_analytics(
            current_user.id
        )

        logger.debug(
            "Dashboard data retrieved",
            user_id=current_user.id,
            total_playlists=playlist_stats["total_playlists"],
        )

        return {
            "stats": {
                "saved_playlists": playlist_stats["saved_playlists"],
                "moods_analyzed": playlist_stats["total_playlists"],
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_tracks": playlist_stats["total_tracks"],
            },
            "recent_activity": recent_playlists_data,
            "mood_distribution": dashboard_analytics.get("mood_distribution", []),
            "audio_insights": dashboard_analytics.get("audio_insights", {}),
            "status_breakdown": dashboard_analytics.get("status_breakdown", {}),
        }

    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get dashboard data: {str(e)}")


@router.get("/quota")
async def get_user_quota(
    current_user: User = Depends(require_auth),
    quota_service: QuotaService = Depends(get_quota_service),
):
    """Get user's daily playlist creation quota status.

    Args:
        current_user: Authenticated user
        quota_service: Quota usage service

    Returns:
        Quota information with usage and limit
    """
    try:
        from app.core.config import settings

        # Get count of playlists created today
        used = await quota_service.get_daily_usage(current_user.id)
        limit = settings.DAILY_PLAYLIST_CREATION_LIMIT
        remaining = max(0, limit - used)

        logger.debug(
            "Quota status retrieved",
            user_id=current_user.id,
            used=used,
            limit=limit,
            remaining=remaining,
        )

        return {
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "can_create": remaining > 0,
            "development": settings.APP_ENV == "development",
        }

    except Exception as e:
        logger.error(f"Error getting quota status: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get quota status: {str(e)}")
