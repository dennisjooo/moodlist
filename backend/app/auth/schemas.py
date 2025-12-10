"""Schemas for authentication workflows and user session data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user (simplified - profile fetched from Spotify)."""

    access_token: str = Field(..., description="Spotify access token")
    refresh_token: str = Field(..., description="Spotify refresh token")
    token_expires_at: datetime = Field(..., description="Token expiration time")


class UserCreateInternal(BaseModel):
    """Internal schema for creating a user with profile data."""

    spotify_id: str = Field(..., description="Spotify user ID")
    email: Optional[EmailStr] = Field(None, description="User email")
    display_name: str = Field(..., description="Display name")
    access_token: str = Field(..., description="Spotify access token")
    refresh_token: str = Field(..., description="Spotify refresh token")
    token_expires_at: datetime = Field(..., description="Token expiration time")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    spotify_id: str
    email: Optional[str]
    display_name: str
    profile_image_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Enable ORM compatibility for SQLAlchemy models."""

        from_attributes = True


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
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime
    created_at: datetime
    last_activity: datetime

    class Config:
        """Enable ORM compatibility for SQLAlchemy models."""

        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    user: Optional[UserResponse] = None
    session: Optional[SessionResponse] = None
    requires_spotify_auth: bool = False
