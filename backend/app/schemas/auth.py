"""Shared authentication schemas exposed to the public API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .user import UserResponse


class LoginRequest(BaseModel):
    """Schema for login request."""

    access_token: str = Field(..., description="Spotify access token")
    refresh_token: str = Field(..., description="Spotify refresh token")


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class SessionResponse(BaseModel):
    """Schema for session response."""

    id: int
    user_id: int
    session_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    last_activity: datetime

    class Config:
        """Enable ORM-mode serialization from SQLAlchemy models."""

        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    user: UserResponse
    session: Optional[SessionResponse] = None
    requires_spotify_auth: bool = False


class LogoutRequest(BaseModel):
    """Schema for logout request."""

    session_token: str = Field(..., description="Session token to invalidate")


class LogoutResponse(BaseModel):
    """Schema for logout response."""

    success: bool
    message: str


class SessionListResponse(BaseModel):
    """Schema for user's active sessions list."""

    sessions: list[SessionResponse]
    total: int


class PasswordResetRequest(BaseModel):
    """Schema for password reset request (future use)."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation (future use)."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")
