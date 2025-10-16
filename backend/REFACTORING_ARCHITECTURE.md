# Proposed Architecture After Refactoring

This document outlines the improved architecture after implementing the suggested refactorings.

## Current Architecture Issues

```
┌─────────────────────────────────────────────────────────────┐
│                         Routes                               │
│  (auth, spotify, playlists, agents)                         │
│                                                              │
│  Problems:                                                   │
│  • Direct HTTP client usage scattered                        │
│  • Business logic mixed with HTTP handling                   │
│  • Direct database queries in routes                         │
│  • Duplicated code across routes                            │
│  • Inconsistent error handling                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
         ┌─────────────────────┐
         │   Database Models    │
         └─────────────────────┘
```

## Proposed Layered Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                          API Layer (Routes)                        │
│                                                                    │
│  • FastAPI route handlers                                         │
│  • Request/response validation (Pydantic schemas)                 │
│  • Authentication/authorization                                   │
│  • Minimal business logic                                         │
│                                                                    │
│  Files: app/*/routes.py                                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ↓
┌───────────────────────────────────────────────────────────────────┐
│                        Service Layer                               │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │ Token Service    │  │ Workflow State   │  │ Playlist        ││
│  │                  │  │ Service          │  │ Service         ││
│  │ • Token refresh  │  │ • State mgmt     │  │ • CRUD ops      ││
│  │ • Token validate │  │ • Cache/DB sync  │  │ • Formatting    ││
│  └──────────────────┘  └──────────────────┘  │ • Validation    ││
│                                               └─────────────────┘│
│                                                                    │
│  Files: app/services/*.py                                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ↓
┌───────────────────────────────────────────────────────────────────┐
│                      Repository Layer                              │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │ User Repository  │  │ Playlist Repo    │  │ Session Repo    ││
│  │                  │  │                  │  │                 ││
│  │ • CRUD           │  │ • CRUD           │  │ • CRUD          ││
│  │ • Query builders │  │ • Query builders │  │ • Query helpers ││
│  └──────────────────┘  └──────────────────┘  └─────────────────┘│
│                                                                    │
│  Files: app/repositories/*.py                                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ↓
┌───────────────────────────────────────────────────────────────────┐
│                    External Client Layer                           │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                    SpotifyAPIClient                           ││
│  │                                                                ││
│  │  • Centralized HTTP client                                    ││
│  │  • Automatic retry logic                                      ││
│  │  • Error handling & mapping                                   ││
│  │  • Request/response logging                                   ││
│  │  • Rate limiting                                              ││
│  │                                                                ││
│  │  Methods:                                                     ││
│  │  • get_user_profile()                                         ││
│  │  • get_user_top_tracks()                                      ││
│  │  • create_playlist()                                          ││
│  │  • refresh_token()                                            ││
│  │  • search_tracks()                                            ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  Files: app/clients/spotify_client.py                            │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ↓
┌───────────────────────────────────────────────────────────────────┐
│                         Data Layer                                 │
│                                                                    │
│  • Database models (SQLAlchemy)                                   │
│  • Database connection management                                 │
│                                                                    │
│  Files: app/models/*.py, app/core/database.py                    │
└───────────────────────────────────────────────────────────────────┘
```

## Cross-Cutting Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Utilities                            │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐│
│  │ Logging    │  │ Constants  │  │ Exceptions │  │ Factories ││
│  │            │  │            │  │            │  │           ││
│  │ • structlog│  │ • Enums    │  │ • Custom   │  │ • LLM     ││
│  │ • Config   │  │ • Status   │  │   exception│  │ • Agent   ││
│  │            │  │ • Timeouts │  │   classes  │  │           ││
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘│
│                                                                  │
│  Files: app/core/*.py                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Responsibilities

### 1. API Layer (Routes)
**Responsibility:** HTTP request/response handling only

```python
@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(
    playlist_id: int,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Get playlist by ID. Thin handler delegates to service."""
    try:
        playlist = await playlist_service.get_playlist(
            playlist_id=playlist_id,
            user_id=current_user.id
        )
        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))
        return PlaylistDetail.from_orm(playlist)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error("Failed to get playlist", playlist_id=playlist_id, error=str(e))
        raise InternalServerError("Failed to retrieve playlist")
```

### 2. Service Layer
**Responsibility:** Business logic and orchestration

```python
class PlaylistService:
    """Service for playlist operations."""
    
    def __init__(
        self,
        playlist_repo: PlaylistRepository,
        spotify_client: SpotifyAPIClient,
        workflow_state_service: WorkflowStateService
    ):
        self.playlist_repo = playlist_repo
        self.spotify_client = spotify_client
        self.workflow_state_service = workflow_state_service
    
    async def get_playlist(
        self, 
        playlist_id: int, 
        user_id: int
    ) -> Optional[Playlist]:
        """Get playlist with authorization check."""
        return await self.playlist_repo.get_by_id_for_user(
            playlist_id=playlist_id,
            user_id=user_id
        )
    
    async def save_to_spotify(
        self,
        session_id: str,
        user_id: int,
        access_token: str
    ) -> PlaylistCreationResult:
        """Save playlist to Spotify (orchestration logic)."""
        # Get state
        state = await self.workflow_state_service.get_state(session_id)
        
        # Create on Spotify
        spotify_playlist = await self.spotify_client.create_playlist(
            access_token=access_token,
            name=state.playlist_name,
            tracks=[r.spotify_uri for r in state.recommendations]
        )
        
        # Update database
        await self.playlist_repo.update_spotify_info(
            session_id=session_id,
            spotify_playlist_id=spotify_playlist["id"],
            spotify_url=spotify_playlist["external_urls"]["spotify"]
        )
        
        return PlaylistCreationResult(...)
```

### 3. Repository Layer
**Responsibility:** Data access and query construction

```python
class PlaylistRepository:
    """Repository for playlist data access."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id_for_user(
        self, 
        playlist_id: int, 
        user_id: int
    ) -> Optional[Playlist]:
        """Get playlist by ID with user authorization."""
        query = (
            select(Playlist)
            .where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
                Playlist.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_for_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Playlist]:
        """List playlists for user with filters."""
        query = self._build_user_query(user_id, status)
        query = query.order_by(desc(Playlist.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _build_user_query(
        self, 
        user_id: int, 
        status: Optional[str] = None
    ) -> Select:
        """Build base query for user playlists."""
        query = select(Playlist).where(
            Playlist.user_id == user_id,
            Playlist.deleted_at.is_(None),
            Playlist.status != PlaylistStatus.CANCELLED
        )
        if status:
            query = query.where(Playlist.status == status)
        return query
```

### 4. Client Layer
**Responsibility:** External API communication

```python
class SpotifyAPIClient:
    """Centralized Spotify API client."""
    
    BASE_URL = "https://api.spotify.com/v1"
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = structlog.get_logger(__name__)
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile from Spotify."""
        return await self._get("/me", access_token)
    
    async def create_playlist(
        self,
        access_token: str,
        name: str,
        description: str = "",
        public: bool = True
    ) -> Dict[str, Any]:
        """Create playlist on Spotify."""
        # Get user ID first
        profile = await self.get_user_profile(access_token)
        user_id = profile["id"]
        
        # Create playlist
        return await self._post(
            f"/users/{user_id}/playlists",
            access_token,
            json={
                "name": name,
                "description": description,
                "public": public
            }
        )
    
    async def _get(
        self, 
        endpoint: str, 
        access_token: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request with retry logic."""
        return await self._request("GET", endpoint, access_token, **kwargs)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._build_headers(access_token)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method, url, headers=headers, **kwargs
                    )
                    response.raise_for_status()
                    
                    self.logger.info(
                        "Spotify API request successful",
                        method=method,
                        endpoint=endpoint,
                        status_code=response.status_code
                    )
                    
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                self.logger.error(
                    "Spotify API error",
                    method=method,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    attempt=attempt + 1
                )
                
                # Handle specific status codes
                if e.response.status_code == 401:
                    raise SpotifyAuthError("Invalid or expired token")
                elif e.response.status_code == 429:
                    # Rate limited - wait and retry
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise SpotifyRateLimitError("Rate limit exceeded")
                elif e.response.status_code >= 500:
                    # Server error - retry
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise SpotifyServerError("Spotify server error")
                else:
                    raise SpotifyAPIError(f"Spotify API error: {e.response.status_code}")
                    
            except httpx.RequestError as e:
                self.logger.error(
                    "Spotify API request error",
                    method=method,
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                    
                raise SpotifyConnectionError(f"Failed to connect to Spotify: {str(e)}")
        
        raise SpotifyAPIError("Max retries exceeded")
    
    def _build_headers(self, access_token: str) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
```

## Dependency Injection Pattern

```python
# In app/dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.playlist_repository import PlaylistRepository
from app.repositories.user_repository import UserRepository
from app.clients.spotify_client import SpotifyAPIClient
from app.services.playlist_service import PlaylistService
from app.services.token_service import TokenService
from app.services.workflow_state_service import WorkflowStateService


# Singletons
_spotify_client: Optional[SpotifyAPIClient] = None

def get_spotify_client() -> SpotifyAPIClient:
    """Get Spotify API client singleton."""
    global _spotify_client
    if _spotify_client is None:
        _spotify_client = SpotifyAPIClient()
    return _spotify_client


# Repository dependencies
def get_playlist_repository(
    db: AsyncSession = Depends(get_db)
) -> PlaylistRepository:
    """Get playlist repository."""
    return PlaylistRepository(db)


def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


# Service dependencies
def get_token_service(
    user_repo: UserRepository = Depends(get_user_repository),
    spotify_client: SpotifyAPIClient = Depends(get_spotify_client)
) -> TokenService:
    """Get token service."""
    return TokenService(user_repo, spotify_client)


def get_playlist_service(
    playlist_repo: PlaylistRepository = Depends(get_playlist_repository),
    spotify_client: SpotifyAPIClient = Depends(get_spotify_client),
    workflow_state_service: WorkflowStateService = Depends(get_workflow_state_service)
) -> PlaylistService:
    """Get playlist service."""
    return PlaylistService(playlist_repo, spotify_client, workflow_state_service)


# Usage in routes:
@router.get("/playlists/{playlist_id}")
async def get_playlist(
    playlist_id: int,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """All dependencies injected automatically."""
    return await playlist_service.get_playlist(playlist_id, current_user.id)
```

## Directory Structure After Refactoring

```
backend/
├── app/
│   ├── agents/          # Agent-related code (existing)
│   ├── auth/            # Authentication routes and schemas
│   │   ├── routes.py
│   │   ├── dependencies.py
│   │   └── schemas.py
│   ├── clients/         # NEW: External API clients
│   │   ├── __init__.py
│   │   └── spotify_client.py
│   ├── core/            # Core configuration and utilities
│   │   ├── config.py
│   │   ├── constants.py      # NEW
│   │   ├── exceptions.py     # NEW
│   │   ├── database.py
│   │   └── middleware.py
│   ├── factories/       # NEW: Factory classes
│   │   ├── __init__.py
│   │   └── llm_factory.py
│   ├── models/          # Database models
│   │   ├── user.py
│   │   ├── playlist.py
│   │   ├── session.py
│   │   └── filters.py        # NEW: Query filter helpers
│   ├── repositories/    # NEW: Data access layer
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── playlist_repository.py
│   │   └── session_repository.py
│   ├── schemas/         # NEW: Pydantic schemas (API models)
│   │   ├── __init__.py
│   │   ├── playlist.py
│   │   ├── user.py
│   │   └── auth.py
│   ├── services/        # NEW: Business logic layer
│   │   ├── __init__.py
│   │   ├── token_service.py
│   │   ├── playlist_service.py
│   │   ├── workflow_state_service.py
│   │   └── auth_service.py
│   ├── playlists/       # Playlist routes (simplified)
│   │   └── routes.py
│   ├── spotify/         # Spotify routes (simplified)
│   │   └── routes.py
│   └── main.py
├── tests/               # Tests organized by layer
│   ├── unit/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── clients/
│   ├── integration/
│   └── e2e/
├── REFACTORING_AUDIT.md
├── REFACTORING_QUICK_WINS.md
└── REFACTORING_ARCHITECTURE.md
```

## Benefits of New Architecture

### 1. Separation of Concerns
- Routes only handle HTTP
- Services contain business logic
- Repositories handle data access
- Clients manage external APIs

### 2. Testability
```python
# Easy to test service in isolation
def test_playlist_service():
    # Mock dependencies
    mock_repo = Mock(PlaylistRepository)
    mock_client = Mock(SpotifyAPIClient)
    mock_workflow = Mock(WorkflowStateService)
    
    # Create service with mocks
    service = PlaylistService(mock_repo, mock_client, mock_workflow)
    
    # Test business logic without HTTP or database
    result = await service.get_playlist(1, 100)
```

### 3. Reusability
- SpotifyAPIClient can be used by any service
- Services can be composed
- Repositories can be shared

### 4. Maintainability
- Clear responsibility for each layer
- Easy to find code
- Changes isolated to specific layer
- Consistent patterns throughout

### 5. Scalability
- Easy to add new services
- Easy to add caching at repository level
- Easy to add new external clients
- Easy to add background tasks

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. Create constants, exceptions, and shared utilities
2. Create SpotifyAPIClient
3. Update routes to use SpotifyAPIClient
4. Standardize logging

### Phase 2: Data Layer (Week 2)
1. Create repository base class
2. Create PlaylistRepository
3. Create UserRepository
4. Update routes to use repositories

### Phase 3: Business Layer (Week 3)
1. Create service classes
2. Move business logic from routes to services
3. Create dependency injection functions
4. Update routes to use services

### Phase 4: Cleanup (Week 4)
1. Create Pydantic schemas
2. Remove duplicated code
3. Add comprehensive tests
4. Update documentation

## Code Comparison

### Before (Current)
```python
# In playlists/routes.py - ~100 lines
@router.post("/playlists/{session_id}/save-to-spotify")
async def save_playlist_to_spotify(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Token refresh (duplicated code)
        current_user = await refresh_spotify_token_if_expired(current_user, db)
        
        # Complex state management (duplicated logic)
        workflow_config = WorkflowConfig(...)
        workflow_manager = WorkflowManager(...)
        state = workflow_manager.get_workflow_state(session_id)
        
        if not state:
            # Database query (should be in repository)
            query = select(Playlist).where(...)
            result = await db.execute(query)
            playlist = result.scalar_one_or_none()
            
            # Complex state reconstruction
            # ... 50 lines ...
        
        # Spotify API call (should be in client)
        state = await playlist_creation_service.create_playlist(state)
        
        # Database update (should be in repository)
        query = select(Playlist).where(...)
        # ...
        
        return {...}
    except Exception as e:
        logger.error(...)
        raise HTTPException(...)
```

### After (Proposed)
```python
# In playlists/routes.py - ~20 lines
@router.post("/playlists/{session_id}/save-to-spotify",
             response_model=PlaylistCreationResponse)
async def save_playlist_to_spotify(
    session_id: str,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service)
):
    """Save playlist to Spotify. Thin handler delegates to service."""
    result = await playlist_service.save_to_spotify(
        session_id=session_id,
        user_id=current_user.id,
        access_token=current_user.access_token
    )
    return PlaylistCreationResponse.from_result(result)


# In services/playlist_service.py - well-organized, testable
class PlaylistService:
    async def save_to_spotify(
        self,
        session_id: str,
        user_id: int,
        access_token: str
    ) -> PlaylistCreationResult:
        """Business logic in service, easy to test."""
        # Get state (delegated to WorkflowStateService)
        state = await self.workflow_state_service.get_or_load_state(session_id)
        
        # Create on Spotify (delegated to SpotifyAPIClient)
        spotify_playlist = await self.spotify_client.create_playlist(
            access_token=access_token,
            name=state.playlist_name,
            tracks=[r.spotify_uri for r in state.recommendations]
        )
        
        # Update database (delegated to Repository)
        await self.playlist_repo.update_spotify_info(
            session_id=session_id,
            spotify_playlist_id=spotify_playlist["id"],
            spotify_url=spotify_playlist["external_urls"]["spotify"]
        )
        
        return PlaylistCreationResult(...)
```

## Conclusion

The proposed architecture:
- **Reduces code duplication** by 30-40%
- **Improves testability** through clear separation of concerns
- **Enhances maintainability** with consistent patterns
- **Enables scalability** through proper layering
- **Follows best practices** from clean architecture and domain-driven design
