import structlog

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SessionConstants
from app.core.exceptions import SpotifyAuthError, UnauthorizedException, InternalServerError
from app.core.database import get_db
from app.clients import SpotifyAPIClient
from app.models.user import User
from app.models.session import Session
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
from app.dependencies import get_user_repository, get_session_repository, get_playlist_repository
from app.agents.core.cache import cache_manager

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)



@router.post("/login", response_model=TokenResponse)
async def register(
    request: Request,
    user_data: UserCreate,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """Register a new user by fetching profile from Spotify."""
    logger.info("Registration attempt with Spotify token")
    
    # Fetch user profile from Spotify using centralized client
    spotify_client = SpotifyAPIClient()
    try:
        profile_data = await spotify_client.get_user_profile(user_data.access_token)
    except SpotifyAuthError as e:
        logger.error("Failed to fetch Spotify profile", error=str(e))
        raise SpotifyAuthError("Invalid Spotify access token or failed to fetch profile")
    except Exception as e:
        logger.error("Unexpected error fetching Spotify profile", error=str(e))
        raise InternalServerError("Failed to authenticate with Spotify")
    
    logger.info("Profile fetched successfully", spotify_id=profile_data["id"])
    
    # Create or update user
    profile_image_url = None
    if profile_data.get("images") and len(profile_data["images"]) > 0:
        profile_image_url = profile_data["images"][0]["url"]
    
    user = await user_repo.create_or_update_user(
        spotify_id=profile_data["id"],
        access_token=user_data.access_token,
        refresh_token=user_data.refresh_token,
        token_expires_at=user_data.token_expires_at,
        display_name=profile_data.get("display_name", "Unknown User"),
        email=profile_data.get("email"),
        profile_image_url=profile_image_url,
        commit=True
    )
    
    logger.info("User created/updated", user_id=user.id, spotify_id=user.spotify_id)
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SessionConstants.EXPIRATION_HOURS)

    # Clean up any existing sessions for this user to prevent conflicts
    await session_repo.delete_user_sessions(user.id)

    session = await session_repo.create_session_for_user(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
        commit=True
    )

    # Set session cookie using utility
    set_session_cookie(response, session_token)
    
    # Create JWT tokens
    token_data = {"sub": user.spotify_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    logger.info("Registration successful", user_id=user.id, spotify_id=user.spotify_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Refresh access token using refresh token."""
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
    # Clear session cookie using utility
    delete_session_cookie(response)

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
    session_token = request.cookies.get(SessionConstants.COOKIE_NAME)

    if not session_token:
        logger.debug("Auth verification failed - no session token")
        return AuthResponse(
            user=None,
            requires_spotify_auth=True
        )

    # Create cache key based on session token
    cache_key = f"auth_verify:{session_token}"

    # Try to get from cache first
    cached_result = await cache_manager.cache.get(cache_key)
    if cached_result is not None:
        logger.debug("Auth verification cache hit", session_token=session_token[:8] + "...")
        return cached_result

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

    await cache_manager.cache.set(cache_key, result, ttl=cache_ttl)

    return result


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