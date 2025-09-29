import structlog
import httpx

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.user import User
from app.models.session import Session
from app.auth.security import (
    create_access_token, 
    create_refresh_token, 
    verify_token,
    generate_session_token,
    encrypt_token
)
from app.auth.dependencies import get_current_user_optional
from app.auth.schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    AuthResponse
)

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Login with Spotify tokens and get JWT tokens."""
    logger.info("Login attempt", ip=request.client.host)
    
    # Find user by tokens (in production, tokens should be encrypted)
    result = await db.execute(
        select(User).where(
            and_(
                User.access_token == login_data.access_token,
                User.refresh_token == login_data.refresh_token,
                User.is_active == True
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    session = Session(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800  # 30 minutes
    )
    
    # Create JWT tokens
    token_data = {"sub": user.spotify_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    logger.info("Login successful", user_id=user.id, spotify_id=user.spotify_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,  # 1 hour
        user=UserResponse.from_orm(user)
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: Request,
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user by fetching profile from Spotify."""
    logger.info("Registration attempt with Spotify token")
    
    # Fetch user profile from Spotify using access token
    async with httpx.AsyncClient() as client:
        try:
            profile_response = await client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {user_data.access_token}"}
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error("Failed to fetch Spotify profile", error=str(e), status_code=e.response.status_code)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Spotify access token or failed to fetch profile"
            )
    
    logger.info("Profile fetched successfully", spotify_id=profile_data["id"])
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.spotify_id == profile_data["id"])
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Update existing user's tokens and profile
        existing_user.access_token = encrypt_token(user_data.access_token)
        existing_user.refresh_token = encrypt_token(user_data.refresh_token)
        existing_user.token_expires_at = user_data.token_expires_at
        existing_user.display_name = profile_data.get("display_name", existing_user.display_name)
        existing_user.email = profile_data.get("email", existing_user.email)
        if profile_data.get("images"):
            existing_user.profile_image_url = profile_data["images"][0]["url"]
        existing_user.is_active = True
        
        await db.commit()
        await db.refresh(existing_user)
        user = existing_user
        logger.info("Updated existing user", user_id=user.id, spotify_id=user.spotify_id)
    else:
        # Create new user
        profile_image_url = None
        if profile_data.get("images") and len(profile_data["images"]) > 0:
            profile_image_url = profile_data["images"][0]["url"]
            
        user = User(
            spotify_id=profile_data["id"],
            email=profile_data.get("email"),
            display_name=profile_data.get("display_name", "Unknown User"),
            access_token=encrypt_token(user_data.access_token),
            refresh_token=encrypt_token(user_data.refresh_token),
            token_expires_at=user_data.token_expires_at,
            profile_image_url=profile_image_url,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created new user", user_id=user.id, spotify_id=user.spotify_id)
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    session = Session(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800
    )
    
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
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    logger.info("Token refresh attempt")
    
    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    result = await db.execute(
        select(User).where(
            and_(
                User.spotify_id == payload["sub"],
                User.is_active == True
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
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
    current_user: User = Depends(get_current_user_optional)
):
    """Logout user and clear session."""
    # Clear session cookie
    response.delete_cookie(
        key="session_token",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    if current_user:
        logger.info("Logout successful", user_id=current_user.id, spotify_id=current_user.spotify_id)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_optional)
):
    """Get current user information."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return UserResponse.from_orm(current_user)


@router.get("/verify", response_model=AuthResponse)
async def verify_auth(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Verify authentication status."""
    if not current_user:
        return AuthResponse(
            user=None,
            requires_spotify_auth=True
        )
    
    return AuthResponse(
        user=UserResponse.from_orm(current_user),
        requires_spotify_auth=False
    )