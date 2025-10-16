# Quick Win Refactorings

These refactorings can be done quickly (< 1 hour each) and provide immediate value.

## 1. Replace Print Statements with Logger (5 minutes)

**File:** `app/main.py`

**Before:**
```python
print(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
print(f"Initializing cache manager with Valkey at {settings.REDIS_URL}")
print("No Valkey URL provided, using in-memory cache")
print(f"Shutting down {settings.APP_NAME}")
```

**After:**
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Starting application", app_name=settings.APP_NAME, environment=settings.APP_ENV)
logger.info("Initializing cache manager with Valkey", redis_url=settings.REDIS_URL)
logger.info("No Valkey URL provided, using in-memory cache")
logger.info("Shutting down application", app_name=settings.APP_NAME)
```

---

## 2. Create Constants for Magic Strings (15 minutes)

**Create:** `app/core/constants.py`

```python
"""Application-wide constants."""
from enum import Enum


class PlaylistStatus(str, Enum):
    """Playlist status values."""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TimeRange(str, Enum):
    """Spotify time range values."""
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class SessionConstants:
    """Session-related constants."""
    EXPIRATION_HOURS = 24
    EXPIRATION_SECONDS = 86400
    COOKIE_NAME = "session_token"


class SpotifyAPIConstants:
    """Spotify API constants."""
    BASE_URL = "https://api.spotify.com/v1"
    ACCOUNTS_URL = "https://accounts.spotify.com/api/token"
```

**Then update usage:**
```python
# In playlists/routes.py
from app.core.constants import PlaylistStatus

# Instead of:
playlist.status = "pending"

# Use:
playlist.status = PlaylistStatus.PENDING
```

---

## 3. Fix Settings Import (10 minutes)

**Files:** `app/auth/routes.py`

**Before:**
```python
def logout(...):
    # ...
    from app.core.config import settings
    is_production = settings.APP_ENV == "production"
```

**After:**
```python
from app.core.config import settings

def logout(...):
    # ...
    is_production = settings.APP_ENV == "production"
```

---

## 4. Standardize Datetime Usage (15 minutes)

**Throughout codebase:**

**Before:**
```python
from datetime import datetime

playlist.deleted_at = datetime.utcnow()  # Naive datetime
```

**After:**
```python
from datetime import datetime, timezone

playlist.deleted_at = datetime.now(timezone.utc)  # Timezone-aware
```

**Files to update:**
- `app/playlists/routes.py` (line 287)
- Any other places using `datetime.utcnow()`

---

## 5. Create Cookie Helper (20 minutes)

**Create:** `app/auth/cookie_utils.py`

```python
"""Cookie management utilities."""
from fastapi import Response

from app.core.config import settings
from app.core.constants import SessionConstants


def set_session_cookie(response: Response, session_token: str) -> None:
    """Set session cookie with standard parameters.
    
    Args:
        response: FastAPI response object
        session_token: Session token value
    """
    is_production = settings.APP_ENV == "production"
    
    response.set_cookie(
        key=SessionConstants.COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=SessionConstants.EXPIRATION_SECONDS,
        path="/"
    )


def delete_session_cookie(response: Response) -> None:
    """Delete session cookie.
    
    Args:
        response: FastAPI response object
    """
    is_production = settings.APP_ENV == "production"
    
    response.delete_cookie(
        key=SessionConstants.COOKIE_NAME,
        httponly=True,
        secure=is_production,
        samesite="lax",
        path="/"
    )
```

**Update usage in `app/auth/routes.py`:**
```python
from app.auth.cookie_utils import set_session_cookie, delete_session_cookie

# In login endpoint:
set_session_cookie(response, session_token)

# In logout endpoint:
delete_session_cookie(response)
```

---

## 6. Create Pydantic Response Models (30 minutes)

**Create:** `app/playlists/schemas.py`

```python
"""Playlist schemas for API responses."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PlaylistSummary(BaseModel):
    """Summary of a playlist for list views."""
    id: int
    session_id: str
    mood_prompt: str
    status: str
    track_count: Optional[int] = None
    name: Optional[str] = None
    spotify_url: Optional[str] = None
    spotify_uri: Optional[str] = None
    spotify_playlist_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PlaylistDetail(PlaylistSummary):
    """Detailed playlist information."""
    duration_ms: Optional[int] = None
    playlist_data: Optional[Dict[str, Any]] = None
    recommendations_data: Optional[list] = None
    mood_analysis_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class PlaylistStatsResponse(BaseModel):
    """User's playlist statistics."""
    total_playlists: int
    completed_playlists: int
    total_tracks: int
    user_id: int
```

**Update routes:**
```python
@router.get("/playlists", response_model=List[PlaylistSummary])
async def get_user_playlists(...):
    # ...
    return [PlaylistSummary.from_orm(p) for p in playlists]
```

---

## 7. Consolidate HTTPException Patterns (30 minutes)

**Create:** `app/core/exceptions.py`

```python
"""Custom exceptions and exception factories."""
from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Resource not found exception."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} {identifier} not found"
        )


class UnauthorizedException(HTTPException):
    """Unauthorized access exception."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class ForbiddenException(HTTPException):
    """Forbidden access exception."""
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ValidationException(HTTPException):
    """Validation error exception."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class SpotifyAPIException(HTTPException):
    """Spotify API error exception."""
    def __init__(self, detail: str = "Spotify API request failed"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail
        )
```

**Usage:**
```python
from app.core.exceptions import NotFoundException, ValidationException

# Instead of:
if not playlist:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Playlist not found"
    )

# Use:
if not playlist:
    raise NotFoundException("Playlist", str(playlist_id))
```

---

## 8. Standardize Logging Library (30 minutes)

**Update all files to use structlog:**

```bash
# Find all files using standard logging
grep -r "import logging" app/ --include="*.py"

# Update each file:
# Before:
import logging
logger = logging.getLogger(__name__)

# After:
import structlog
logger = structlog.get_logger(__name__)
```

**Key files to update:**
- `app/playlists/routes.py`
- `app/agents/routes/agent_routes.py`
- `app/playlists/services/*.py`
- All agent files

---

## 9. Create Spotify API Endpoints Constants (10 minutes)

**Update:** `app/core/constants.py`

```python
class SpotifyEndpoints:
    """Spotify API endpoint paths."""
    
    # Base URLs
    API_BASE = "https://api.spotify.com/v1"
    ACCOUNTS_BASE = "https://accounts.spotify.com/api"
    
    # User endpoints
    USER_PROFILE = "/me"
    USER_TOP_TRACKS = "/me/top/tracks"
    USER_TOP_ARTISTS = "/me/top/artists"
    USER_PLAYLISTS = "/me/playlists"
    
    # Playlist endpoints
    PLAYLISTS = "/playlists"
    PLAYLIST_TRACKS = "/playlists/{playlist_id}/tracks"
    
    # Search endpoints
    SEARCH = "/search"
    
    # Track endpoints
    TRACKS = "/tracks"
    TRACK_DETAILS = "/tracks/{track_id}"
    
    # Auth endpoints
    TOKEN = "/token"
```

---

## 10. Extract Common Query Filters (20 minutes)

**Create:** `app/models/filters.py`

```python
"""Common database query filters."""
from sqlalchemy import and_
from sqlalchemy.sql import Select

from app.models.playlist import Playlist


def filter_active_playlists(query: Select) -> Select:
    """Add filter for non-deleted playlists.
    
    Args:
        query: SQLAlchemy select query
        
    Returns:
        Query with deleted filter applied
    """
    return query.where(Playlist.deleted_at.is_(None))


def filter_user_playlists(query: Select, user_id: int, 
                         include_cancelled: bool = False) -> Select:
    """Add filter for user's playlists.
    
    Args:
        query: SQLAlchemy select query
        user_id: User ID to filter by
        include_cancelled: Whether to include cancelled playlists
        
    Returns:
        Query with user filter applied
    """
    conditions = [
        Playlist.user_id == user_id,
        Playlist.deleted_at.is_(None)
    ]
    
    if not include_cancelled:
        conditions.append(Playlist.status != "cancelled")
    
    return query.where(and_(*conditions))


def filter_by_status(query: Select, status: str) -> Select:
    """Add status filter to query.
    
    Args:
        query: SQLAlchemy select query
        status: Status to filter by
        
    Returns:
        Query with status filter applied
    """
    return query.where(Playlist.status == status)
```

**Usage:**
```python
from app.models.filters import filter_user_playlists, filter_by_status

# Instead of:
query = select(Playlist).where(
    Playlist.user_id == current_user.id,
    Playlist.deleted_at.is_(None),
    Playlist.status != "cancelled"
)

# Use:
query = select(Playlist)
query = filter_user_playlists(query, current_user.id)
if status:
    query = filter_by_status(query, status)
```

---

## Summary

These 10 quick wins will:
- Remove ~150-200 lines of duplicate code
- Improve code consistency
- Make the codebase more maintainable
- Provide better type safety
- Improve error messages
- Make testing easier

**Total Time: ~3-4 hours**

**Files to Create:**
1. `app/core/constants.py`
2. `app/core/exceptions.py`
3. `app/auth/cookie_utils.py`
4. `app/playlists/schemas.py`
5. `app/models/filters.py`

**Files to Modify:**
- `app/main.py`
- `app/auth/routes.py`
- `app/playlists/routes.py`
- All files using `logging` instead of `structlog`
- All files using `datetime.utcnow()`
