"""User-facing schemas for profile data, stats, and admin responses."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    spotify_id: str
    email: Optional[EmailStr] = None
    display_name: str
    profile_image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Enable ORM attribute loading for SQLAlchemy models."""
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Schema for detailed user profile response."""
    id: int
    spotify_id: str
    email: Optional[EmailStr] = None
    display_name: str
    profile_image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Aggregated stats
    total_playlists: int = 0
    total_invocations: int = 0
    last_playlist_created: Optional[datetime] = None

    class Config:
        """Enable ORM attribute loading for SQLAlchemy models."""
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Schema for updating user profile."""
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None
    is_active: Optional[bool] = None


class UserStatsResponse(BaseModel):
    """Schema for user statistics response."""
    user_id: int
    total_playlists: int
    total_invocations: int
    playlists_this_month: int
    invocations_this_month: int
    average_playlist_tracks: float
    most_common_mood: Optional[str] = None
    last_activity: Optional[datetime] = None


class UserListResponse(BaseModel):
    """Schema for paginated user list response (admin use)."""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
