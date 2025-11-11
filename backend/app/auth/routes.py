import structlog

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer

from app.core.constants import SessionConstants
from app.core.exceptions import SpotifyAuthError, UnauthorizedException, InternalServerError
from app.clients import SpotifyAPIClient
from app.models.user import User
from app.auth.security import (
    create_access_token, 
    create_refresh_token, 
    verify_token,
    generate_session_token
)
from app.auth.dependencies import require_auth
from app.auth.cookie_utils import set_session_cookie, delete_session_cookie
from app.auth.schemas import (
    UserCreate,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    AuthResponse
)
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.playlist_repository import PlaylistRepository
from app.services.quota_service import QuotaService
from app.dependencies import (
    get_user_repository,
    get_session_repository,
    get_playlist_repository,
    get_quota_service,
)
from app.agents.core.cache import cache_manager
from app.core.limiter import limiter

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)



@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """Register a new user by fetching profile from Spotify.
    
    OPTIMIZED VERSION with:
    - UPSERT for user creation/update (1 query instead of 2)
    - Atomic session replacement (1 query instead of 2)
    - Performance timing and logging
    
    Rate limit: 10 requests per minute per IP address.
    """
    import time
    start_time = time.time()
    
    logger.info("Login attempt", ip=request.client.host)
    
    # Fetch user profile from Spotify using centralized client
    from app.core.config import settings
    spotify_client = SpotifyAPIClient()
    is_whitelisted = True  # Default to True

    try:
        profile_data = await spotify_client.get_user_profile(user_data.access_token)

        # If in dev mode, test if user can actually use the API
        # Some users might authenticate successfully but not be whitelisted
        if settings.SPOTIFY_DEV_MODE:
            try:
                # Ping /me again to verify API access (not just OAuth)
                await spotify_client.get_user_profile(user_data.access_token)
                is_whitelisted = True
            except SpotifyAuthError as test_error:
                test_error_msg = str(test_error)
                if "403" in test_error_msg or "Insufficient permissions" in test_error_msg or "permissions" in test_error_msg.lower():
                    logger.error("User authenticated but not whitelisted for API access",
                               spotify_id=profile_data.get("id"),
                               error=test_error_msg,
                               ip=request.client.host)
                    is_whitelisted = False
                    raise SpotifyAuthError(
                        "NOT_WHITELISTED: Your Spotify account is not whitelisted for beta access. "
                        "MoodList is currently in limited beta (25 users max). "
                        "Please request access to be added to the whitelist."
                    )
                # Other errors, re-raise
                raise

    except SpotifyAuthError as e:
        error_msg = str(e)

        # If already marked as NOT_WHITELISTED, re-raise as-is
        if "NOT_WHITELISTED" in error_msg:
            raise

        # If in dev mode and we get a 403-type error, it's likely a whitelist issue
        if settings.SPOTIFY_DEV_MODE and ("403" in error_msg or "Insufficient permissions" in error_msg or "permissions" in error_msg.lower()):
            logger.error("User not whitelisted in Spotify dev mode", error=error_msg, ip=request.client.host)
            raise SpotifyAuthError(
                "NOT_WHITELISTED: Your Spotify account is not whitelisted for beta access. "
                "MoodList is currently in limited beta (25 users max). "
                "Please request access to be added to the whitelist."
            )

        logger.error("Failed to fetch Spotify profile", error=error_msg)
        raise SpotifyAuthError("Invalid Spotify access token or failed to fetch profile")
    except Exception as e:
        logger.error("Unexpected error fetching Spotify profile", error=str(e))
        raise InternalServerError("Failed to authenticate with Spotify")
    
    spotify_fetch_time = time.time() - start_time
    logger.debug("Spotify profile fetched", duration_ms=spotify_fetch_time * 1000)
    
    # Extract profile data
    profile_image_url = None
    if profile_data.get("images") and len(profile_data["images"]) > 0:
        profile_image_url = profile_data["images"][0]["url"]
    
    # OPTIMIZED: Single-query upsert
    db_start = time.time()
    user = await user_repo.upsert_user(
        spotify_id=profile_data["id"],
        access_token=user_data.access_token,
        refresh_token=user_data.refresh_token,
        token_expires_at=user_data.token_expires_at,
        display_name=profile_data.get("display_name", "Unknown User"),
        email=profile_data.get("email"),
        profile_image_url=profile_image_url,
        is_spotify_whitelisted=is_whitelisted,
    )
    
    # OPTIMIZED: Atomic session replacement
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SessionConstants.EXPIRATION_HOURS)
    
    await session_repo.replace_user_session_atomic(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
    )
    
    # Commit transaction
    await session_repo.session.commit()
    
    db_time = time.time() - db_start
    logger.debug("Database operations completed", duration_ms=db_time * 1000)

    # Set session cookie using utility (pass origin for localhost detection)
    origin = request.headers.get("origin")
    set_session_cookie(response, session_token, origin)
    
    # Create JWT tokens
    token_data = {"sub": user.spotify_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    total_time = time.time() - start_time
    logger.info(
        "Login successful",
        user_id=user.id,
        spotify_id=user.spotify_id,
        total_duration_ms=total_time * 1000,
        spotify_duration_ms=spotify_fetch_time * 1000,
        db_duration_ms=db_time * 1000
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repository)
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
        user=UserResponse.from_orm(user)
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    session_repo: SessionRepository = Depends(get_session_repository),
    current_user: Optional[User] = Depends(require_auth)
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

        logger.info("Logout successful", user_id=current_user.id, spotify_id=current_user.spotify_id)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(require_auth)
):
    """Get current user information."""
    if not current_user:
        raise UnauthorizedException("Not authenticated")

    return UserResponse.from_orm(current_user)


@router.get("/verify", response_model=AuthResponse)
async def verify_auth(
    request: Request,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    """
    Verify authentication status with optimized session-based auth and caching.

    Performance optimization: Single database query with join instead of multiple lookups,
    plus server-side caching to reduce database load.
    Before: 2-3 queries (session lookup + user lookup)
    After: 1 query with eager loading + 5-minute cache
    """
    try:
        session_token = request.cookies.get(SessionConstants.COOKIE_NAME)

        if not session_token:
            logger.debug("Auth verification failed - no session token")
            return AuthResponse(
                user=None,
                requires_spotify_auth=True
            )

        # Create cache key based on session token
        cache_key = f"auth_verify:{session_token}"

        # Try to get from cache first (with error handling)
        try:
            cached_result = await cache_manager.cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Auth verification cache hit", session_token=session_token[:8] + "...")
                return cached_result
        except Exception as cache_error:
            logger.warning("Cache get failed, continuing without cache", error=str(cache_error))
            # Continue without cache

        # Single optimized query: get session with user in one go
        session = await session_repo.get_valid_session_with_user(session_token)

        if not session or not session.user:
            logger.debug("Auth verification failed - invalid session or no user",
                        has_session=bool(session), has_user=bool(session.user if session else False))
            result = AuthResponse(
                user=None,
                requires_spotify_auth=True
            )
        elif not session.user.is_active:
            logger.debug("Auth verification failed - user not active", user_id=session.user.id)
            result = AuthResponse(
                user=None,
                requires_spotify_auth=True
            )
        else:
            logger.debug("Auth verification successful",
                        user_id=session.user.id,
                        spotify_id=session.user.spotify_id,
                        session_id=session.id)
            result = AuthResponse(
                user=UserResponse.from_orm(session.user),
                requires_spotify_auth=False
            )

        # Cache with TTL based on session expiration time
        # If session expires soon (< 1 hour), cache for shorter time
        # If session is fresh (> 12 hours left), cache longer
        now = datetime.now(timezone.utc)
        if session and session.expires_at:
            time_until_expiry = (session.expires_at - now).total_seconds()
            if time_until_expiry < 3600:  # Less than 1 hour left
                cache_ttl = 60  # Cache for 1 minute
            elif time_until_expiry > 43200:  # More than 12 hours left
                cache_ttl = 1800  # Cache for 30 minutes
            else:
                cache_ttl = 300  # Cache for 5 minutes (default)
        else:
            cache_ttl = 300  # Default 5 minutes

        try:
            await cache_manager.cache.set(cache_key, result, ttl=cache_ttl)
        except Exception as cache_error:
            logger.warning("Cache set failed", error=str(cache_error))
            # Continue without caching

        return result

    except Exception as e:
        logger.error("Auth verification failed with exception",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True)
        # Return unauthenticated response on error
        return AuthResponse(
            user=None,
            requires_spotify_auth=True
        )


@router.get("/dashboard")
async def get_user_dashboard(
    current_user: User = Depends(require_auth),
    playlist_repo: PlaylistRepository = Depends(get_playlist_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
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
        total_sessions = await session_repo.get_session_count(user_id=current_user.id, active_only=False)
        active_sessions = await session_repo.get_session_count(user_id=current_user.id, active_only=True)
        
        # Get recent playlists for activity timeline and mood analysis
        recent_playlists_data = await playlist_repo.get_user_recent_playlists(
            user_id=current_user.id,
            limit=10
        )
        
        # Get mood distribution and audio features analysis
        dashboard_analytics = await playlist_repo.get_user_dashboard_analytics(current_user.id)
        
        logger.debug(
            "Dashboard data retrieved",
            user_id=current_user.id,
            total_playlists=playlist_stats["total_playlists"]
        )
        
        return {
            "stats": {
                "saved_playlists": playlist_stats["saved_playlists"],
                "moods_analyzed": playlist_stats["total_playlists"],
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_tracks": playlist_stats["total_tracks"]
            },
            "recent_activity": recent_playlists_data,
            "mood_distribution": dashboard_analytics.get("mood_distribution", []),
            "audio_insights": dashboard_analytics.get("audio_insights", {}),
            "status_breakdown": dashboard_analytics.get("status_breakdown", {})
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
            remaining=remaining
        )
        
        return {
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "can_create": remaining > 0,
            "development": settings.APP_ENV == "development"
        }
    
    except Exception as e:
        logger.error(f"Error getting quota status: {str(e)}", exc_info=True)
        raise InternalServerError(f"Failed to get quota status: {str(e)}")
