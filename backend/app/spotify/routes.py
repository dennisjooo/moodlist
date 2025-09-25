import httpx
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/profile")
async def get_spotify_profile(
    current_user: User = Depends(get_current_user),
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


@router.get("/token/refresh")
async def refresh_spotify_token(
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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