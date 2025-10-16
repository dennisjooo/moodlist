from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.core.constants import SpotifyEndpoints
from app.core.exceptions import (
    ValidationException,
    InternalServerError,
    SpotifyAuthError,
    SpotifyAPIException
)
from app.clients import SpotifyAPIClient
from app.models.user import User
from app.auth.dependencies import require_auth, refresh_spotify_token_if_expired

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/token")
async def exchange_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Exchange authorization code for Spotify access tokens."""
    logger.info("Exchanging authorization code for tokens")

    # Get code from query parameters
    code = request.query_params.get("code")
    if not code:
        raise ValidationException("Authorization code is required")

    # Validate required environment variables
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        logger.error("Spotify credentials not configured")
        raise InternalServerError("Server configuration error")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET
            }

            response = await client.post(
                SpotifyEndpoints.TOKEN_URL,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

            # Validate required fields
            if not token_data.get("access_token") or not token_data.get("refresh_token"):
                logger.error("Invalid token response from Spotify")
                raise SpotifyAPIException("Invalid token response from Spotify")

            logger.info("Token exchange successful")

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data.get("expires_in", 3600),
                "token_type": token_data.get("token_type", "Bearer")
            }

        except httpx.HTTPStatusError as e:
            logger.error("Token exchange failed", error=str(e), status_code=e.response.status_code)
            if e.response.status_code == 400:
                raise ValidationException("Invalid authorization code or redirect URI")
            raise SpotifyAPIException("Failed to exchange authorization code")
        except Exception as e:
            logger.error("Unexpected error during token exchange", error=str(e))
            raise InternalServerError("Internal server error")


@router.get("/profile")
async def get_spotify_profile(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Spotify profile information."""
    logger.info("Getting Spotify profile", user_id=current_user.id)

    # Refresh token if expired
    current_user = await refresh_spotify_token_if_expired(current_user, db)

    # Use centralized Spotify client
    spotify_client = SpotifyAPIClient()
    try:
        profile_data = await spotify_client.get_user_profile(current_user.access_token)
        
        return {
            "id": profile_data["id"],
            "display_name": profile_data["display_name"],
            "email": profile_data.get("email"),
            "images": profile_data.get("images", []),
            "country": profile_data.get("country"),
            "followers": profile_data.get("followers", {}).get("total", 0),
            "product": profile_data.get("product")
        }
    except SpotifyAuthError as e:
        logger.error("Failed to get Spotify profile", error=str(e))
        raise SpotifyAuthError("Failed to get Spotify profile")
    except Exception as e:
        logger.error("Unexpected error getting Spotify profile", error=str(e))
        raise InternalServerError("Failed to get Spotify profile")


@router.get("/profile/public")
async def get_spotify_profile_public(
    access_token: str = Query(..., description="Spotify access token"),
    db: AsyncSession = Depends(get_db)
):
    """Get Spotify profile information using access token (no auth required)."""
    logger.info("Getting Spotify profile with access token")

    # Validate access token
    if not access_token or not access_token.strip():
        raise SpotifyAuthError("Access token is required")

    # Remove Bearer prefix if present
    token = access_token.replace("Bearer ", "").strip()

    # Use centralized Spotify client
    spotify_client = SpotifyAPIClient()
    try:
        profile_data = await spotify_client.get_user_profile(token)

        # Validate required fields
        if not profile_data.get("id") or not profile_data.get("display_name"):
            logger.error("Invalid profile response from Spotify")
            raise SpotifyAPIException("Invalid profile data received from Spotify")

        logger.info("Profile fetch successful", spotify_id=profile_data["id"])

        return {
            "id": profile_data["id"],
            "display_name": profile_data["display_name"],
            "email": profile_data.get("email"),
            "images": profile_data.get("images", []),
            "country": profile_data.get("country"),
            "followers": profile_data.get("followers", {}).get("total", 0)
        }
    except SpotifyAuthError as e:
        logger.error("Failed to get Spotify profile - auth error", error=str(e))
        raise SpotifyAuthError("Invalid or expired access token")
    except Exception as e:
        logger.error("Unexpected error during profile fetch", error=str(e))
        raise InternalServerError("Failed to get Spotify profile")


@router.get("/token/refresh")
async def refresh_spotify_token(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Refresh the user's Spotify access token."""
    logger.info("Refreshing Spotify token", user_id=current_user.id)
    
    # Use centralized Spotify client
    spotify_client = SpotifyAPIClient()
    try:
        token_data = await spotify_client.refresh_token(current_user.refresh_token)
        
        # Update user's tokens in database
        current_user.access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            current_user.refresh_token = token_data["refresh_token"]
        
        await db.commit()
        
        return {
            "access_token": token_data["access_token"],
            "expires_in": token_data.get("expires_in", 3600),
            "token_type": token_data.get("token_type", "Bearer")
        }
    except SpotifyAuthError as e:
        logger.error("Failed to refresh Spotify token", error=str(e))
        raise SpotifyAuthError("Failed to refresh Spotify token")
    except Exception as e:
        logger.error("Unexpected error refreshing Spotify token", error=str(e))
        raise InternalServerError("Failed to refresh Spotify token")


@router.get("/playlists")
async def get_user_playlists(
    current_user: User = Depends(require_auth),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Spotify playlists."""
    # Refresh token if expired
    current_user = await refresh_spotify_token_if_expired(current_user, db)
    
    logger.info("Getting user playlists", user_id=current_user.id, limit=limit, offset=offset)
    
    # Use centralized Spotify client
    spotify_client = SpotifyAPIClient()
    try:
        playlists_data = await spotify_client.get_user_playlists(
            current_user.access_token,
            limit=limit,
            offset=offset
        )
        
        return {
            "items": playlists_data.get("items", []),
            "total": playlists_data.get("total", 0),
            "limit": playlists_data.get("limit", limit),
            "offset": playlists_data.get("offset", offset)
        }
    except SpotifyAuthError as e:
        logger.error("Failed to get user playlists", error=str(e))
        raise SpotifyAuthError("Failed to get user playlists")
    except Exception as e:
        logger.error("Unexpected error getting playlists", error=str(e))
        raise InternalServerError("Failed to get user playlists")


@router.get("/search/tracks")
async def search_tracks(
    query: str = Query(..., min_length=1, description="Search query for tracks"),
    limit: int = Query(default=20, le=50, description="Maximum number of results"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Search Spotify tracks for adding to playlists."""
    logger.info("Searching tracks", user_id=current_user.id, query=query, limit=limit)
    
    # Refresh token if expired
    current_user = await refresh_spotify_token_if_expired(current_user, db)
    
    # Use centralized Spotify client
    spotify_client = SpotifyAPIClient()
    try:
        search_data = await spotify_client.search_tracks(
            current_user.access_token,
            query=query,
            limit=limit
        )
        
        # Extract and format track results
        tracks = search_data.get("tracks", {}).get("items", [])
        formatted_tracks = [
            {
                "track_id": track["id"],
                "track_name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "spotify_uri": track["uri"],
                "album": track["album"]["name"],
                "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                "duration_ms": track["duration_ms"],
                "preview_url": track.get("preview_url")
            }
            for track in tracks
        ]
        
        return {
            "tracks": formatted_tracks,
            "total": len(formatted_tracks),
            "query": query
        }
    except SpotifyAuthError as e:
        logger.error("Failed to search tracks", error=str(e))
        raise SpotifyAuthError("Failed to search tracks")
    except Exception as e:
        logger.error("Unexpected error searching tracks", error=str(e))
        raise InternalServerError("Failed to search tracks")