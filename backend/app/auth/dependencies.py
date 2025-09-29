import structlog
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import verify_token
from app.core.database import get_db
from app.models.session import Session
from app.models.user import User

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
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
            detail="User not found or inactive",
        )
    
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            return None
        
        result = await db.execute(
            select(User).where(
                and_(
                    User.spotify_id == payload["sub"],
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()
        return user
    except Exception:
        return None


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[Session]:
    """Get current session from session token."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    
    result = await db.execute(
        select(Session).where(
            and_(
                Session.session_token == session_token,
                Session.expires_at > datetime.now(timezone.utc)
            )
        )
    )
    session = result.scalar_one_or_none()
    return session


async def require_auth(
    user: Optional[User] = Depends(get_current_user_optional),
    session: Optional[Session] = Depends(get_current_session),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Require authentication via either JWT token or session."""
    if not user and not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    # If we have a session but no user, get user from session
    if not user and session:
        result = await db.execute(
            select(User).where(
                and_(
                    User.id == session.user_id,
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return user


async def get_user_from_spotify_tokens(
    access_token: str,
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get user from Spotify tokens (for OAuth callback)."""
    # Note: In production, tokens should be encrypted in the database
    # For now, we'll do a simple lookup
    result = await db.execute(
        select(User).where(
            and_(
                User.access_token == access_token,
                User.refresh_token == refresh_token,
                User.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()

