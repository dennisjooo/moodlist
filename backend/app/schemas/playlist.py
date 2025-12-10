"""Playlist API schemas for requests, responses, and data projections."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlaylistTrack(BaseModel):
    """Schema for individual track in playlist."""

    id: str
    name: str
    artist: str
    album: str
    duration_ms: int
    spotify_url: str
    preview_url: Optional[str] = None
    image_url: Optional[str] = None


class PlaylistUser(BaseModel):
    """Nested user info for playlist responses."""

    id: int
    display_name: str
    profile_image_url: Optional[str] = None


class PlaylistResponse(BaseModel):
    """Schema for playlist response."""

    id: int
    user_id: int
    session_id: Optional[str] = None
    spotify_playlist_id: Optional[str] = None
    mood_prompt: str
    playlist_data: Optional[Dict[str, Any]] = None
    recommendations_data: Optional[Dict[str, Any]] = None
    mood_analysis_data: Optional[Dict[str, Any]] = None
    track_count: int
    duration_ms: int
    status: str
    error_message: Optional[str] = None

    # LLM-generated triadic color scheme
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    color_tertiary: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    # Nested user info
    user: Optional[PlaylistUser] = None

    class Config:
        """Allow constructing responses from ORM objects."""

        from_attributes = True


class PlaylistCreateRequest(BaseModel):
    """Schema for creating a new playlist."""

    mood_prompt: str = Field(
        ..., description="User's mood description for playlist generation"
    )


class PlaylistUpdateRequest(BaseModel):
    """Schema for updating playlist metadata."""

    mood_prompt: Optional[str] = None
    playlist_data: Optional[Dict[str, Any]] = None
    recommendations_data: Optional[Dict[str, Any]] = None
    mood_analysis_data: Optional[Dict[str, Any]] = None
    track_count: Optional[int] = None
    duration_ms: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class PlaylistListResponse(BaseModel):
    """Schema for paginated playlist list response."""

    playlists: List[PlaylistResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PlaylistGenerationStatus(BaseModel):
    """Schema for playlist generation status."""

    playlist_id: int
    status: str
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    error_message: Optional[str] = None
