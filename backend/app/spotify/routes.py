import httpx
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import require_auth
from app.core.config import settings

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )

    # Validate required environment variables
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        logger.error("Spotify credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )

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
                "https://accounts.spotify.com/api/token",
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

            # Validate required fields
            if not token_data.get("access_token") or not token_data.get("refresh_token"):
                logger.error("Invalid token response from Spotify")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid token response from Spotify"
                )

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid authorization code or redirect URI"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
        except Exception as e:
            logger.error("Unexpected error during token exchange", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.get("/profile")
async def get_spotify_profile(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Spotify profile information."""
    logger.info("Getting Spotify profile", user_id=current_user.id)

    # Use the stored access token to get profile from Spotify
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {current_user.access_token}"}
            )
            response.raise_for_status()
            profile_data = response.json()

            return {
                "id": profile_data["id"],
                "display_name": profile_data["display_name"],
                "email": profile_data.get("email"),
                "images": profile_data.get("images", []),
                "country": profile_data.get("country"),
                "followers": profile_data.get("followers", {}).get("total", 0),
                "product": profile_data.get("product")
            }

        except httpx.HTTPStatusError as e:
            logger.error("Failed to get Spotify profile", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Spotify profile"
            )


@router.get("/profile/public")
async def get_spotify_profile_public(
    access_token: str = Query(..., description="Spotify access token"),
    db: AsyncSession = Depends(get_db)
):
    """Get Spotify profile information using access token (no auth required)."""
    logger.info("Getting Spotify profile with access token")

    # Validate access token
    if not access_token or not access_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required"
        )

    # Remove Bearer prefix if present
    token = access_token.replace("Bearer ", "").strip()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            profile_data = response.json()

            # Validate required fields
            if not profile_data.get("id") or not profile_data.get("display_name"):
                logger.error("Invalid profile response from Spotify")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid profile data received from Spotify"
                )

            logger.info("Profile fetch successful", spotify_id=profile_data["id"])

            return {
                "id": profile_data["id"],
                "display_name": profile_data["display_name"],
                "email": profile_data.get("email"),
                "images": profile_data.get("images", []),
                "country": profile_data.get("country"),
                "followers": profile_data.get("followers", {}).get("total", 0)
            }

        except httpx.HTTPStatusError as e:
            logger.error("Failed to get Spotify profile", error=str(e), status_code=e.response.status_code)
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired access token"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Spotify profile"
            )
        except Exception as e:
            logger.error("Unexpected error during profile fetch", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.get("/token/refresh")
async def refresh_spotify_token(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Refresh the user's Spotify access token."""
    logger.info("Refreshing Spotify token", user_id=current_user.id)
    
    # Use refresh token to get new access token
    async with httpx.AsyncClient() as client:
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": current_user.refresh_token,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET
            }
            
            response = await client.post(
                "https://accounts.spotify.com/api/token",
                data=data
            )
            response.raise_for_status()
            token_data = response.json()
            
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
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to refresh Spotify token", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to refresh Spotify token"
            )


@router.get("/playlists")
async def get_user_playlists(
    current_user: User = Depends(require_auth),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Spotify playlists."""
    logger.info("Getting user playlists", user_id=current_user.id, limit=limit, offset=offset)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.spotify.com/v1/me/playlists?limit={limit}&offset={offset}",
                headers={"Authorization": f"Bearer {current_user.access_token}"}
            )
            response.raise_for_status()
            playlists_data = response.json()
            
            return {
                "items": playlists_data.get("items", []),
                "total": playlists_data.get("total", 0),
                "limit": playlists_data.get("limit", limit),
                "offset": playlists_data.get("offset", offset)
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to get user playlists", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user playlists"
            )


@router.post("/playlists/create")
async def create_playlist(
    name: str = Query(..., description="Playlist name"),
    description: str = Query(default="", description="Playlist description"),
    public: bool = Query(default=True, description="Whether playlist is public"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Create a new playlist on Spotify."""
    logger.info("Creating playlist", user_id=current_user.id, name=name)
    
    async with httpx.AsyncClient() as client:
        try:
            # First create the playlist
            create_data = {
                "name": name,
                "description": description,
                "public": public
            }
            
            response = await client.post(
                "https://api.spotify.com/v1/me/playlists",
                headers={"Authorization": f"Bearer {current_user.access_token}"},
                json=create_data
            )
            response.raise_for_status()
            playlist_data = response.json()
            
            return {
                "id": playlist_data["id"],
                "name": playlist_data["name"],
                "description": playlist_data.get("description", ""),
                "public": playlist_data.get("public", False),
                "external_urls": playlist_data.get("external_urls", {}),
                "uri": playlist_data["uri"]
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to create playlist", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create playlist"
            )


@router.post("/playlists/{playlist_id}/tracks")
async def add_tracks_to_playlist(
    playlist_id: str,
    track_uris: list = Query(..., description="List of Spotify track URIs"),
    position: Optional[int] = Query(default=None, description="Position to add tracks"),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Add tracks to a Spotify playlist."""
    logger.info("Adding tracks to playlist", user_id=current_user.id, playlist_id=playlist_id, track_count=len(track_uris))
    
    async with httpx.AsyncClient() as client:
        try:
            data = {"uris": track_uris}
            if position is not None:
                data["position"] = position
            
            response = await client.post(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                headers={"Authorization": f"Bearer {current_user.access_token}"},
                json=data
            )
            response.raise_for_status()
            result_data = response.json()
            
            return {
                "snapshot_id": result_data.get("snapshot_id"),
                "message": f"Added {len(track_uris)} tracks to playlist"
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to add tracks to playlist", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add tracks to playlist"
            )