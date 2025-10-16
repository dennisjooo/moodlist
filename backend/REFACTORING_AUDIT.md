# Backend Refactoring Audit

This document outlines refactoring opportunities identified in the `/backend` directory, organized by priority and impact.

## Table of Contents
1. [High Priority Refactorings](#high-priority-refactorings)
2. [Medium Priority Refactorings](#medium-priority-refactorings)
3. [Low Priority Refactorings](#low-priority-refactorings)
4. [Technical Debt](#technical-debt)

---

## High Priority Refactorings

### 1. Inconsistent Logging Implementation
**Impact:** High  
**Effort:** Medium  
**Files Affected:** ~50+ files

**Issue:**
- Mixed usage of `logging` and `structlog` throughout the codebase
- Inconsistent logger initialization patterns
- Some files use `logger = logging.getLogger(__name__)`, others use `logger = structlog.get_logger(__name__)`

**Current State:**
```python
# In auth/routes.py
import structlog
logger = structlog.get_logger(__name__)

# In playlists/routes.py
import logging
logger = logging.getLogger(__name__)

# In agents/routes/agent_routes.py
import logging
logger = logging.getLogger(__name__)
```

**Recommended Fix:**
- Standardize on `structlog` (already partially adopted)
- Create a logging configuration module that all files import from
- Update all logger initializations to use structlog consistently

**Benefits:**
- Consistent structured logging across the application
- Better log querying and analysis
- Improved debugging experience

---

### 2. Duplicated Spotify API Client Code
**Impact:** High  
**Effort:** Medium  
**Files Affected:** 6+ files

**Issue:**
- Multiple files create their own `httpx.AsyncClient()` instances for Spotify API calls
- No centralized error handling for Spotify API errors
- Repeated authentication header setup

**Affected Files:**
- `app/auth/routes.py` (lines 46-60)
- `app/auth/dependencies.py` (lines 187-237)
- `app/spotify/routes.py` (multiple functions)
- `app/playlists/services/spotify_edit_service.py`
- `app/agents/workflows/workflow_manager.py`
- `app/agents/recommender/recommendation_generator/token_manager.py`

**Current State:**
```python
# Repeated pattern in multiple files:
async with httpx.AsyncClient() as client:
    try:
        response = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Failed to...", error=str(e))
        raise HTTPException(...)
```

**Recommended Fix:**
Create a centralized `SpotifyAPIClient` class:

```python
# app/clients/spotify_client.py
class SpotifyAPIClient:
    """Centralized Spotify API client with built-in error handling."""
    
    BASE_URL = "https://api.spotify.com/v1"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def get(self, endpoint: str, access_token: str, **kwargs):
        """Make GET request to Spotify API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self._get_headers(access_token),
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise self._handle_error(e)
    
    # Similar methods for post, put, delete
    
    def _get_headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _handle_error(self, error: httpx.HTTPStatusError):
        # Centralized error handling with specific error types
        pass
```

**Benefits:**
- DRY principle - remove duplicated code
- Centralized error handling
- Easier to add retry logic, rate limiting, or monitoring
- Single point for Spotify API changes

---

### 3. Duplicated Token Refresh Logic
**Impact:** High  
**Effort:** Low  
**Files Affected:** 2 files

**Issue:**
- Token refresh logic is duplicated between dependency function and route endpoint
- Same Spotify token exchange code in multiple places

**Affected Files:**
- `app/auth/dependencies.py` (lines 157-237) - `refresh_spotify_token_if_expired()`
- `app/spotify/routes.py` (lines 198-241) - `/token/refresh` endpoint

**Current State:**
```python
# In auth/dependencies.py
async def refresh_spotify_token_if_expired(user: User, db: AsyncSession) -> User:
    # 80 lines of token refresh logic
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": user.refresh_token,
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "client_secret": settings.SPOTIFY_CLIENT_SECRET
        }
        response = await client.post(...)
    # ...

# In spotify/routes.py
@router.get("/token/refresh")
async def refresh_spotify_token(...):
    # Similar token refresh logic duplicated
```

**Recommended Fix:**
Create a `TokenService` class:

```python
# app/services/token_service.py
class TokenService:
    """Service for managing Spotify token operations."""
    
    @staticmethod
    async def refresh_token(refresh_token: str) -> Dict[str, Any]:
        """Refresh Spotify access token."""
        # Single implementation of token refresh logic
        pass
    
    @staticmethod
    async def refresh_user_token_if_expired(user: User, db: AsyncSession) -> User:
        """Check and refresh user token if expired."""
        # Uses refresh_token() internally
        pass
```

**Benefits:**
- Single source of truth for token refresh logic
- Easier to test and maintain
- Consistent behavior across the application

---

### 4. Duplicated Profile Fetching Logic
**Impact:** Medium-High  
**Effort:** Low  
**Files Affected:** 2 files

**Issue:**
- Spotify profile fetching code is duplicated
- Two separate endpoints for essentially the same operation

**Affected Files:**
- `app/auth/routes.py` (lines 46-60) - login endpoint
- `app/spotify/routes.py` (lines 94-131, 133-195) - two profile endpoints

**Recommended Fix:**
- Use the centralized SpotifyAPIClient (from #2)
- Or create a `ProfileService` to handle profile operations
- Consolidate the two profile endpoints into one with optional auth

---

## Medium Priority Refactorings

### 5. Settings Import Inconsistency
**Impact:** Medium  
**Effort:** Low  
**Files Affected:** Multiple

**Issue:**
- Settings imported inside functions instead of module level
- Inconsistent import patterns

**Affected Files:**
- `app/auth/routes.py` (line 129, 214) - imports inside functions
- Multiple other files

**Current State:**
```python
# In auth/routes.py line 129
def logout(...):
    from app.core.config import settings  # Inside function
    is_production = settings.APP_ENV == "production"
```

**Recommended Fix:**
```python
# At top of file
from app.core.config import settings

def logout(...):
    is_production = settings.APP_ENV == "production"
```

**Benefits:**
- Consistent code style
- Easier to mock in tests
- Clear dependencies at file level

---

### 6. Hardcoded Values and Magic Numbers
**Impact:** Medium  
**Effort:** Low  
**Files Affected:** Multiple

**Issue:**
- Session expiration times, cookie parameters, and other values hardcoded
- Magic strings for status values

**Examples:**
```python
# In auth/routes.py
expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # Hardcoded 24
max_age=86400  # Hardcoded seconds

# Throughout codebase
playlist.status = "pending"  # Magic string
playlist.status = "completed"  # Magic string
playlist.status = "cancelled"  # Magic string
```

**Recommended Fix:**
```python
# In app/core/constants.py
from enum import Enum

class PlaylistStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

# Session constants
SESSION_EXPIRATION_HOURS = 24
SESSION_EXPIRATION_SECONDS = SESSION_EXPIRATION_HOURS * 3600
```

**Benefits:**
- Type safety with enums
- Single source of truth for constants
- Easier to modify values
- Better IDE autocomplete

---

### 7. Duplicated Database Query Patterns
**Impact:** Medium  
**Effort:** Medium  
**Files Affected:** `app/playlists/routes.py`, other route files

**Issue:**
- Similar query patterns repeated across routes
- Filtering logic duplicated

**Examples:**
```python
# Repeated pattern for user ownership check:
query = select(Playlist).where(
    Playlist.id == playlist_id,
    Playlist.user_id == current_user.id,
    Playlist.deleted_at.is_(None)
)

# Similar code in multiple endpoints
```

**Recommended Fix:**
Create a `PlaylistRepository` class:

```python
# app/repositories/playlist_repository.py
class PlaylistRepository:
    """Repository for playlist database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, playlist_id: int, user_id: int, 
                        include_deleted: bool = False) -> Optional[Playlist]:
        """Get playlist by ID with ownership check."""
        query = select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == user_id
        )
        if not include_deleted:
            query = query.where(Playlist.deleted_at.is_(None))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_session(self, session_id: str, user_id: int) -> Optional[Playlist]:
        """Get playlist by session ID."""
        # ...
    
    async def list_user_playlists(self, user_id: int, 
                                  status: Optional[str] = None,
                                  limit: int = 50, 
                                  offset: int = 0) -> List[Playlist]:
        """List user's playlists with filters."""
        # ...
```

**Benefits:**
- DRY principle
- Testable business logic separate from HTTP layer
- Consistent query patterns
- Easier to add caching later

---

### 8. Duplicated Playlist Response Formatting
**Impact:** Medium  
**Effort:** Low  
**Files Affected:** `app/playlists/routes.py`

**Issue:**
- Playlist-to-dict conversion logic duplicated in multiple endpoints

**Affected Functions:**
- `get_user_playlists()` (lines 88-113)
- `get_playlist()` (lines 172-186)
- `get_playlist_by_session()` (lines 229-243)

**Recommended Fix:**
Create response serializers using Pydantic:

```python
# app/playlists/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PlaylistResponse(BaseModel):
    """Playlist response schema."""
    id: int
    session_id: str
    mood_prompt: str
    status: str
    track_count: Optional[int] = None
    duration_ms: Optional[int] = None
    name: Optional[str] = None
    spotify_url: Optional[str] = None
    spotify_uri: Optional[str] = None
    spotify_playlist_id: Optional[str] = None
    mood_analysis_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm_with_playlist_data(cls, playlist: Playlist):
        """Create from ORM with nested playlist_data extraction."""
        data = {
            "id": playlist.id,
            "session_id": playlist.session_id,
            # ... extract all fields including nested ones
        }
        return cls(**data)
```

**Benefits:**
- Consistent response format
- Automatic validation
- Clear API schema
- Easier to modify response structure

---

### 9. Cookie Management Duplication
**Impact:** Medium  
**Effort:** Low  
**Files Affected:** `app/auth/routes.py`

**Issue:**
- Cookie setting and deletion logic duplicated

**Affected Lines:**
- Lines 132-140 (setting cookie in login)
- Lines 217-223 (deleting cookie in logout)
- Cookie parameters repeated

**Recommended Fix:**
```python
# app/auth/cookie_manager.py
class CookieManager:
    """Manages authentication cookies."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def set_session_cookie(self, response: Response, session_token: str):
        """Set session cookie with standard parameters."""
        is_production = self.settings.APP_ENV == "production"
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=86400,
            path="/"
        )
    
    def delete_session_cookie(self, response: Response):
        """Delete session cookie."""
        is_production = self.settings.APP_ENV == "production"
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=is_production,
            samesite="lax",
            path="/"
        )
```

---

### 10. Error Handling Pattern Duplication
**Impact:** Medium  
**Effort:** Medium  
**Files Affected:** Most route files

**Issue:**
- Similar try-except patterns throughout route handlers
- Inconsistent error responses

**Current Pattern:**
```python
try:
    # Business logic
    return result
except HTTPException:
    raise
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed: {str(e)}"
    )
```

**Recommended Fix:**
Create error handling decorators or use FastAPI exception handlers:

```python
# app/core/error_handlers.py
from functools import wraps

def handle_route_errors(operation_name: str):
    """Decorator for consistent error handling in routes."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation_name}: {str(e)}"
                )
        return wrapper
    return decorator

# Usage:
@router.get("/playlists/{playlist_id}")
@handle_route_errors("get playlist")
async def get_playlist(...):
    # Business logic without try-except
    pass
```

---

### 11. Workflow State Management Complexity
**Impact:** Medium  
**Effort:** High  
**Files Affected:** `app/playlists/routes.py`, `app/agents/routes/agent_routes.py`

**Issue:**
- Complex logic to retrieve state from cache vs database
- State reconstruction logic scattered
- Duplicated state management code

**Affected Code:**
- `save_playlist_to_spotify()` function (lines 468-622 in playlists/routes.py)
- Large function with mixed responsibilities

**Recommended Fix:**
Create a `WorkflowStateService`:

```python
# app/services/workflow_state_service.py
class WorkflowStateService:
    """Service for managing workflow state across cache and database."""
    
    def __init__(self, workflow_manager: WorkflowManager, db: AsyncSession):
        self.workflow_manager = workflow_manager
        self.db = db
    
    async def get_state(self, session_id: str) -> Optional[AgentState]:
        """Get workflow state from cache or database."""
        # Check cache first
        state = self.workflow_manager.get_workflow_state(session_id)
        if state:
            return state
        
        # Fall back to database
        return await self._load_from_database(session_id)
    
    async def _load_from_database(self, session_id: str) -> Optional[AgentState]:
        """Reconstruct state from database."""
        # Extract reconstruction logic here
        pass
    
    async def save_state(self, state: AgentState):
        """Save state to both cache and database."""
        pass
```

---

## Low Priority Refactorings

### 12. Agent/LLM Initialization Duplication
**Impact:** Low  
**Effort:** Medium  
**Files Affected:** 2 files

**Issue:**
- Multiple ChatOpenAI instances created with similar configurations
- Agent initialization duplicated

**Affected Files:**
- `app/agents/routes/agent_routes.py` (lines 35-54)
- `app/playlists/routes.py` (lines 33-38)

**Recommended Fix:**
Create an LLM factory:

```python
# app/factories/llm_factory.py
class LLMFactory:
    """Factory for creating LLM instances."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def create_openrouter_llm(self, model: str = "moonshotai/kimi-k2:free", 
                             temperature: float = 1):
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://openrouter.ai/api/v1",
            api_key=self.settings.OPENROUTER_API_KEY
        )
    
    def create_groq_llm(self, model: str = "openai/gpt-oss-120b",
                       temperature: float = 1):
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://api.groq.com/openai/v1",
            api_key=self.settings.GROQ_API_KEY
        )
    
    def create_cerebras_llm(self, model: str = "gpt-oss-120b",
                           temperature: float = 1):
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://api.cerebras.ai/v1",
            api_key=self.settings.CEREBRAS_API_KEY
        )
```

---

### 13. Configuration Cleanup
**Impact:** Low  
**Effort:** Low  
**Files Affected:** `app/core/config.py`

**Issue:**
- Unused configuration fields (AWS_REGION, RDS_* fields when DATABASE_URL is used)
- `get_database_url()` method exists but DATABASE_URL is used directly in most places

**Recommended Fix:**
- Remove unused fields or clearly document their purpose
- Consistently use either DATABASE_URL or get_database_url()
- Consider splitting into environment-specific configs

---

### 14. Middleware Cleanup
**Impact:** Low  
**Effort:** Low  
**Files Affected:** `app/core/middleware.py`

**Issues:**
- `InvocationStatusMiddleware` is mostly empty (lines 174-189)
- `DatabaseMiddleware` may not be needed if using Depends(get_db)
- `LoggingMiddleware` has complex logic that could be simplified

**Recommended Fix:**
- Remove or implement InvocationStatusMiddleware properly
- Consider removing DatabaseMiddleware if not used
- Simplify LoggingMiddleware

---

## Technical Debt

### 15. Datetime Handling Inconsistency
**Files:** Multiple  
**Issue:** Mix of timezone-aware and naive datetimes

```python
# In auth/dependencies.py (line 176)
if token_expires_at.tzinfo is None:
    token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

# In playlists/routes.py (line 287)
playlist.deleted_at = datetime.utcnow()  # Naive datetime
```

**Recommended Fix:**
- Always use timezone-aware datetimes
- Use `datetime.now(timezone.utc)` instead of `datetime.utcnow()`
- Add database migration to ensure all datetime columns are timezone-aware

---

### 16. Missing Type Hints
**Impact:** Low  
**Effort:** Medium  
**Issue:** Some functions lack complete type hints

**Recommended Fix:**
- Add type hints to all function signatures
- Use mypy for type checking
- Add type hints to class attributes

---

### 17. Print Statements in Production Code
**Files:** `app/main.py`  
**Lines:** 20, 25, 28, 37

**Issue:** Using `print()` instead of proper logging

```python
print(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
```

**Recommended Fix:**
```python
logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
```

---

## Implementation Priority

### Phase 1 (Immediate - High Impact, Low/Medium Effort)
1. Standardize logging (structlog everywhere)
2. Fix print statements to use logger
3. Create SpotifyAPIClient
4. Consolidate token refresh logic
5. Add constants/enums for magic strings

### Phase 2 (Short-term - High/Medium Impact)
1. Implement Repository pattern for database queries
2. Create response serializers with Pydantic
3. Centralize cookie management
4. Create error handling decorators
5. Fix datetime handling inconsistency

### Phase 3 (Medium-term - Code Quality)
1. Implement WorkflowStateService
2. Create LLM factory
3. Clean up middleware
4. Add comprehensive type hints
5. Configuration cleanup

---

## Estimated Impact

| Refactoring | Lines Saved | Bugs Prevented | Maintainability | Testability |
|-------------|-------------|----------------|-----------------|-------------|
| Logging Standardization | ~50 | Medium | High | Medium |
| SpotifyAPIClient | ~200 | High | High | High |
| Token Service | ~100 | Medium | High | High |
| Repository Pattern | ~150 | Low | High | High |
| Constants/Enums | ~30 | Medium | Medium | Medium |
| Cookie Manager | ~40 | Low | Medium | High |
| Error Handlers | ~100 | Low | High | Medium |

**Total Estimated Lines Reduced:** ~670 lines  
**Estimated Effort:** 2-3 weeks for all phases

---

## Notes

- This audit was conducted on the current state of the codebase
- Some refactorings depend on others (e.g., SpotifyAPIClient should be done before TokenService)
- Breaking changes should be done carefully with adequate testing
- Consider creating feature flags for major refactorings to enable gradual rollout
