# Remaining Refactoring Work

## 🎯 **Remaining Tasks Summary**

### **Phase 3: Architectural Layers (High Priority)**

#### 1. **Repository Layer** - Create `app/repositories/`

- `base_repository.py` - Base class with common database operations
- `playlist_repository.py` - Playlist CRUD operations
- `user_repository.py` - User data operations
- `session_repository.py` - Session management operations

#### 2. **Service Layer** - Create `app/services/`

- `token_service.py` - Token refresh and validation logic
- `playlist_service.py` - Business logic for playlist operations
- `workflow_state_service.py` - Workflow state management
- `auth_service.py` - Authentication business logic

#### 3. **Response Schemas** - Create `app/schemas/`

- `playlist.py` - Pydantic models for playlist responses
- `user.py` - User response models
- `auth.py` - Authentication response models

### **Phase 4: Service Integration (Medium Priority)**

#### 4. **Update Playlist Services** - 9 files in `app/playlists/services/`

Files needing updates:

- `playlist_creation_service.py`
- `playlist_edit_service.py`
- `spotify_edit_service.py`
- `track_adder.py`
- `playlist_describer.py`
- `playlist_namer.py`
- `playlist_summarizer.py`
- `playlist_validator.py`

**Changes needed:**

- Replace `httpx.AsyncClient()` with `SpotifyAPIClient`
- Replace `HTTPException` with custom exceptions
- Replace `logging.getLogger()` with `structlog.get_logger()`
- Use constants from `app.core.constants`

#### 5. **Update Agent Services** - Multiple files in `app/agents/`

Files needing updates (52 files total):

- All files in `app/agents/recommender/`
- All files in `app/agents/tools/`
- All files in `app/agents/workflows/`
- All files in `app/agents/core/`

**Changes needed:**

- Replace `logging.getLogger()` with `structlog.get_logger()` (52 files)
- Replace direct Spotify API calls with `SpotifyAPIClient` (8 remaining instances)

### **Phase 5: Final Cleanup (Low Priority)**

#### 6. **Code Cleanup** - Scattered issues

- Replace remaining `HTTPException` usage (7 files still have some)
- Replace any remaining magic strings
- Ensure consistent datetime usage (`datetime.now(timezone.utc)`)

#### 7. **Dependency Injection** - FastAPI integration

- Implement DI pattern for services and repositories
- Update route handlers to use injected dependencies
- Add proper service lifecycle management

#### 8. **Testing Infrastructure** - Quality assurance

- Unit tests for all new services and repositories
- Integration tests for service interactions
- Error handling test coverage

## 📊 **Current State Metrics**

- **Completed**: Phases 1-2 (~95% infrastructure done)
- **Remaining HTTP clients**: 8 instances across 5 files
- **Remaining logging fixes**: 52 files
- **Remaining HTTPException**: Some usage in 7 files
- **Phase 3 completed**: All architectural directories and files created

## 🎯 **Recommended Order**

1. **Week 1**: ✅ Repository layer created (4 files)
2. **Week 2**: ✅ Service layer + response schemas created (7 files)
3. **Week 3**: Update playlist services (9 files)
4. **Week 4**: Update agent services (52 files) + final cleanup

## 💡 **Benefits of Completion**

- **Clean Architecture**: Proper separation of concerns
- **Testability**: Services and repositories are easily testable
- **Maintainability**: Changes isolated to specific layers
- **Consistency**: All code uses same patterns and libraries
- **Type Safety**: Pydantic schemas provide validation
- **Reliability**: Centralized error handling and retry logic

---

**Status**: Phase 3 completed - Ready for Phase 4

Phase 3 accomplished: Created repository layer, service layer, and response schemas.
**Estimated Effort**: 4-6 weeks for all remaining work
**Risk Level**: Medium (incremental changes, backwards compatible)
