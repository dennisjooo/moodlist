# Frontend Refactoring Opportunities

## Overview
This document outlines refactoring opportunities identified in the MoodList frontend codebase. The recommendations preserve the existing workspace context (AI playlist generation with Spotify integration) while improving code maintainability, testability, and developer experience.

---

## 1. AuthContext: Extract Cache Management into Custom Hook

### Current State
`src/lib/contexts/AuthContext.tsx` (Lines 18-62)

The cache management logic is embedded directly in the AuthContext component, mixing responsibilities.

### Issue
- Cache operations (get/set/clear) are mixed with auth context logic
- Not reusable across the application
- Harder to test in isolation
- Violates Single Responsibility Principle

### Recommendation
Create a new custom hook: `src/lib/hooks/auth/useAuthCache.ts`

```typescript
// src/lib/hooks/auth/useAuthCache.ts
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import type { User, CachedAuthData } from '@/lib/types/auth';

export function useAuthCache() {
  const getCachedAuth = (): CachedAuthData | null => {
    if (typeof window === 'undefined') return null;
    try {
      const cached = sessionStorage.getItem(config.auth.cacheKey);
      if (!cached) return null;

      const data: CachedAuthData = JSON.parse(cached);
      const age = Date.now() - data.timestamp;

      if (age > config.auth.cacheTTL) {
        sessionStorage.removeItem(config.auth.cacheKey);
        return null;
      }

      return data;
    } catch (error) {
      logger.warn('Failed to read auth cache', { component: 'useAuthCache', error });
      return null;
    }
  };

  const setCachedAuth = (user: User): void => {
    if (typeof window === 'undefined') return;
    try {
      const data: CachedAuthData = {
        user,
        timestamp: Date.now(),
      };
      sessionStorage.setItem(config.auth.cacheKey, JSON.stringify(data));
    } catch (error) {
      logger.warn('Failed to write auth cache', { component: 'useAuthCache', error });
    }
  };

  const clearCachedAuth = (): void => {
    if (typeof window === 'undefined') return;
    try {
      sessionStorage.removeItem(config.auth.cacheKey);
    } catch (error) {
      logger.warn('Failed to clear auth cache', { component: 'useAuthCache', error });
    }
  };

  return {
    getCachedAuth,
    setCachedAuth,
    clearCachedAuth,
  };
}
```

### Benefits
- ✅ Single Responsibility: Cache logic separated from auth state
- ✅ Reusability: Can be used in other contexts if needed
- ✅ Testability: Easy to unit test cache operations
- ✅ Maintainability: Changes to caching don't affect auth flow

---

## 2. AuthContext: Extract API Service Layer

### Current State
`src/lib/contexts/AuthContext.tsx` (Lines 64-218)

Auth API calls are embedded in the AuthContext, mixing UI state management with data fetching.

### Issue
- Context handles both state AND API calls
- API logic not reusable
- Difficult to test API interactions separately
- Retry logic embedded in component

### Recommendation
Create: `src/lib/api/auth.ts`

```typescript
// src/lib/api/auth.ts
import { config } from '@/lib/config';
import { getAuthCookies } from '../cookies';
import type { User } from '../types/auth';

export interface AuthVerifyResponse {
  user: User | null;
}

export interface AuthLoginRequest {
  access_token: string;
  refresh_token: string;
  token_expires_at: number;
}

class AuthAPI {
  async verifySession(retryCount = 0): Promise<AuthVerifyResponse> {
    const response = await fetch(`${config.api.baseUrl}/api/auth/verify`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthCookies(),
      },
      credentials: 'include',
    });

    if (!response.ok) {
      if (response.status === 401) {
        return { user: null };
      }
      
      // Retry logic for non-auth errors
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 200));
        return this.verifySession(1);
      }
      
      throw new Error(`Auth verification failed: ${response.status}`);
    }

    return response.json();
  }

  async login(request: AuthLoginRequest): Promise<void> {
    const response = await fetch(`${config.api.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
    }
  }

  async logout(): Promise<void> {
    const response = await fetch(`${config.api.baseUrl}/api/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthCookies(),
      },
      credentials: 'include',
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Logout failed: ${response.status} - ${errorText}`);
    }
  }
}

export const authAPI = new AuthAPI();
```

Then create: `src/lib/hooks/auth/useAuthVerification.ts`

```typescript
// src/lib/hooks/auth/useAuthVerification.ts
import { useCallback, useState } from 'react';
import { authAPI } from '@/lib/api/auth';
import { logger } from '@/lib/utils/logger';
import type { User } from '@/lib/types/auth';
import { useAuthCache } from './useAuthCache';

export function useAuthVerification() {
  const [isValidated, setIsValidated] = useState(false);
  const { getCachedAuth, setCachedAuth, clearCachedAuth } = useAuthCache();

  const verifyAuth = useCallback(async (skipCache = false): Promise<User | null> => {
    try {
      // Check cache first (unless explicitly skipped)
      if (!skipCache) {
        const cached = getCachedAuth();
        if (cached) {
          logger.debug('Using cached auth data', { component: 'useAuthVerification' });
          // Start background validation
          setTimeout(() => verifyAuth(true), 0);
          return cached.user;
        }
      }

      // Verify with backend
      const data = await authAPI.verifySession();
      
      if (data.user) {
        logger.info('Auth verification successful', { component: 'useAuthVerification' });
        setCachedAuth(data.user);
        setIsValidated(true);
        window.dispatchEvent(new CustomEvent('auth-validated', { detail: { user: data.user } }));
        return data.user;
      } else {
        logger.info('Auth verification - no user', { component: 'useAuthVerification' });
        clearCachedAuth();
        setIsValidated(true);
        return null;
      }
    } catch (error) {
      logger.error('Auth verification error', error, { component: 'useAuthVerification' });
      clearCachedAuth();
      setIsValidated(true);
      return null;
    }
  }, [getCachedAuth, setCachedAuth, clearCachedAuth]);

  return {
    verifyAuth,
    isValidated,
  };
}
```

### Benefits
- ✅ Separation of Concerns: API logic separate from context
- ✅ Reusability: Auth API can be used anywhere
- ✅ Testability: Mock API layer in tests
- ✅ Consistency: Single source of truth for auth API

---

## 3. Create Session Page: Extract Navigation Logic

### Current State
`src/app/create/[id]/page.tsx` (Lines 43-78)

Complex navigation logic with multiple nested conditions in handleBack function.

### Issue
- Difficult to read and understand flow
- Hard to test navigation logic
- Duplicated referrer checking logic
- Component too large with mixed concerns

### Recommendation
Create: `src/lib/hooks/navigation/useSessionNavigation.ts`

```typescript
// src/lib/hooks/navigation/useSessionNavigation.ts
import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

interface UseSessionNavigationOptions {
  sessionId: string | null;
  isWorkflowActive: boolean;
  onNavigateAway?: () => void;
}

export function useSessionNavigation({
  sessionId,
  isWorkflowActive,
  onNavigateAway,
}: UseSessionNavigationOptions) {
  const router = useRouter();

  const navigateBack = useCallback(() => {
    // Check if we're on edit page
    if (window.location.pathname.includes('/edit')) {
      const parentPath = window.location.pathname.replace('/edit', '');
      router.push(parentPath);
      return;
    }

    // If workflow is active, trigger confirmation dialog
    if (isWorkflowActive && onNavigateAway) {
      onNavigateAway();
      return;
    }

    // Determine best navigation destination
    const destination = determineNavigationDestination(sessionId);
    router.push(destination);
  }, [sessionId, isWorkflowActive, onNavigateAway, router]);

  return {
    navigateBack,
  };
}

function determineNavigationDestination(sessionId: string | null): string {
  const referrer = document.referrer;
  const currentPath = window.location.pathname;

  // If user came from playlists page
  if (referrer.includes('/playlists')) {
    return '/playlists';
  }

  // If user came from /create page
  if (referrer.includes('/create') && !referrer.includes('/create/')) {
    return '/create';
  }

  // If we have a session ID, likely came from playlists
  if (currentPath.includes('/create/') && sessionId) {
    return '/playlists';
  }

  // Default fallback
  return '/playlists';
}
```

### Usage
```typescript
// In CreateSessionPage
const { navigateBack } = useSessionNavigation({
  sessionId: workflowState.sessionId,
  isWorkflowActive: isActive,
  onNavigateAway: () => setShowCancelDialog(true),
});
```

### Benefits
- ✅ Single Responsibility: Navigation logic isolated
- ✅ Testability: Easy to test navigation decisions
- ✅ Reusability: Can be used in other session pages
- ✅ Readability: Clear and documented flow

---

## 4. Playlist Edits: Use Existing useDebouncedSearch Hook

### Current State
`src/lib/hooks/playlist/usePlaylistEdits.ts` (Lines 137-184)

Custom debouncing logic with timeout management and race condition handling.

### Issue
- Duplicates functionality already in `useDebouncedSearch` hook
- More complex than needed
- Harder to maintain

### Recommendation
Refactor to use existing `useDebouncedSearch` hook:

```typescript
// In usePlaylistEdits.ts
import { useDebouncedSearch } from '../ui/useDebouncedSearch';

export function usePlaylistEdits({ sessionId, initialTracks }: UsePlaylistEditsOptions) {
  const { error: showError } = useToast();
  const { applyCompletedEdit, searchTracks: searchTracksApi } = useWorkflow();

  // ... other state ...

  const [searchResults, setSearchResults] = useState<SearchTrack[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Use existing debounced search hook
  const [searchQuery, setSearchQuery, debouncedQuery] = useDebouncedSearch('', undefined, 300);

  // Perform search when debounced value changes
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);

    searchTracksApi(debouncedQuery)
      .then(results => {
        setSearchResults(results.tracks || []);
      })
      .catch(error => {
        logger.error('Search failed', error, { component: 'usePlaylistEdits' });
        showError('Failed to search tracks');
      })
      .finally(() => {
        setIsSearching(false);
      });
  }, [debouncedQuery, searchTracksApi, showError]);

  const isSearchPending = searchQuery !== debouncedQuery;

  return {
    // ... other returns ...
    searchQuery,
    searchResults,
    isSearching,
    isSearchPending,
    searchTracks: setSearchQuery, // Simplified interface
  };
}
```

### Benefits
- ✅ Code Reuse: Leverages existing utilities
- ✅ Simplicity: Less code to maintain
- ✅ Consistency: Standard debouncing pattern
- ✅ Reliability: Race conditions handled by tested hook

---

## 5. WorkflowAPI: Extract Error Handling

### Current State
`src/lib/api/workflow.ts` (Lines 156-175)

Complex error message extraction logic repeated in API layer.

### Issue
- Verbose error handling
- Pattern could be reused in other API services
- Tightly coupled to response structure

### Recommendation
Create: `src/lib/utils/apiErrorHandling.ts`

```typescript
// src/lib/utils/apiErrorHandling.ts
/**
 * Extract error message from API response
 */
export async function extractErrorMessage(response: Response): Promise<string> {
  const defaultMessage = `API request failed: ${response.status} ${response.statusText}`;
  
  try {
    const errorData = await response.json();
    
    // Backend returns error in detail.message for rate limits
    if (errorData.detail?.message) {
      return errorData.detail.message;
    }
    
    // FastAPI validation errors
    if (errorData.detail && typeof errorData.detail === 'string') {
      return errorData.detail;
    }
    
    // Generic message field
    if (errorData.message) {
      return errorData.message;
    }
  } catch {
    // If parsing fails, use default message
  }
  
  return defaultMessage;
}

/**
 * Create a standardized API error
 */
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public endpoint?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}
```

Then update WorkflowAPI:

```typescript
// In WorkflowAPI.request()
if (!response.ok) {
  const errorMessage = await extractErrorMessage(response);
  logger.error('API request failed', undefined, { 
    component: 'WorkflowAPI', 
    status: response.status, 
    endpoint,
    errorMessage 
  });
  throw new APIError(response.status, errorMessage, endpoint);
}
```

### Benefits
- ✅ DRY: Error extraction reusable across all API services
- ✅ Consistency: Standard error format
- ✅ Maintainability: Update error handling in one place
- ✅ Extensibility: Easy to add new error formats

---

## 6. Config: Add Type Definitions

### Current State
`src/lib/config.ts`

Config is marked as const but lacks explicit TypeScript types.

### Issue
- Limited autocomplete support
- No compile-time validation
- Harder to refactor safely

### Recommendation
Add explicit type definitions:

```typescript
// src/lib/config.ts
interface APIConfig {
  readonly baseUrl: string;
}

interface AuthConfig {
  readonly sessionCookieName: string;
  readonly cacheKey: string;
  readonly cacheTTL: number;
}

interface PollingConfig {
  readonly baseInterval: number;
  readonly maxBackoff: number;
  readonly maxRetries: number;
  readonly awaitingInputInterval: number;
  readonly pendingInterval: number;
}

export interface AppConfig {
  readonly api: APIConfig;
  readonly auth: AuthConfig;
  readonly polling: PollingConfig;
}

export const config: AppConfig = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  auth: {
    sessionCookieName: 'session_token',
    cacheKey: 'moodlist_auth_cache',
    cacheTTL: 24 * 60 * 60 * 1000, // 24 hours
  },
  polling: {
    baseInterval: 3000,
    maxBackoff: 30000,
    maxRetries: 3,
    awaitingInputInterval: 10000,
    pendingInterval: 5000,
  },
};
```

### Benefits
- ✅ Type Safety: Catch errors at compile time
- ✅ Better IDE Support: Full autocomplete
- ✅ Documentation: Types serve as inline docs
- ✅ Refactoring: Easier to track config usage

---

## 7. Create Session Page: Simplify Loading State Management

### Current State
`src/app/create/[id]/page.tsx` (Lines 29, 82-136)

Multiple useEffects managing loading state with complex conditions.

### Issue
- Multiple sources of truth for loading state
- Complex interdependencies
- Hard to reason about when loading completes

### Recommendation
Use derived state and consolidate effects:

```typescript
// Derive loading state from workflow state
const isLoadingSession = useMemo(() => {
  // Still loading if we don't have both session ID and status
  if (workflowState.sessionId !== sessionId) return true;
  if (workflowState.status === null && !workflowState.error) return true;
  return false;
}, [workflowState.sessionId, workflowState.status, workflowState.error, sessionId]);

// Single consolidated effect for loading workflow
useEffect(() => {
  if (!sessionId) {
    router.push('/create');
    return;
  }

  // Already loaded this session
  if (workflowState.sessionId === sessionId && workflowState.status !== null) {
    return;
  }

  // Already loading
  if (workflowState.isLoading) {
    return;
  }

  logger.info('[Page] Loading workflow', { component: 'CreateSessionPage', sessionId });
  loadWorkflow(sessionId).catch(error => {
    logger.error('Failed to load workflow', error, { component: 'CreateSessionPage' });
  });
}, [sessionId, workflowState.sessionId, workflowState.status, workflowState.isLoading, router, loadWorkflow]);
```

### Benefits
- ✅ Simplicity: Single source of truth
- ✅ Predictability: Clear loading conditions
- ✅ Maintainability: Fewer effects to track
- ✅ Performance: Derived state, no extra renders

---

## 8. Consistent Use of Utility Functions

### Current State
Terminal status checking appears in multiple places with inline logic.

### Issue
- Inconsistent checks across components
- Harder to update status logic
- Duplicated code

### Recommendation
Ensure consistent use of existing utilities:

```typescript
// Import utility
import { isTerminalStatus } from '@/lib/utils/workflow';

// Instead of:
const isTerminalStatus = workflowState.status === 'completed' || 
                        workflowState.status === 'failed' || 
                        workflowState.status === 'cancelled';

// Use:
const isTerminal = isTerminalStatus(workflowState.status);
```

Update `workflow.ts` to include all status checks:

```typescript
// src/lib/utils/workflow.ts
export function isTerminalStatus(status: string | null): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled';
}

export function isActiveStatus(status: string | null): boolean {
  return status !== null && !isTerminalStatus(status);
}

export function isErrorStatus(status: string | null): boolean {
  return status === 'failed' || status === 'cancelled';
}
```

### Benefits
- ✅ Consistency: Same logic everywhere
- ✅ Maintainability: Update once, apply everywhere
- ✅ Readability: Self-documenting function names
- ✅ Type Safety: Centralized type checking

---

## 9. Extract Workflow Event Management

### Current State
Workflow events are dispatched throughout components (e.g., `workflowEvents.removed()`, `workflowEvents.updated()`).

### Recommendation
Create a centralized event manager hook:

```typescript
// src/lib/hooks/workflow/useWorkflowEvents.ts
import { useCallback } from 'react';
import { workflowEvents } from './useActiveWorkflows';
import { logger } from '@/lib/utils/logger';

export function useWorkflowEvents() {
  const markAsRemoved = useCallback((sessionId: string, reason?: string) => {
    logger.debug('Marking workflow as removed', { 
      component: 'useWorkflowEvents', 
      sessionId,
      reason 
    });
    workflowEvents.removed(sessionId);
  }, []);

  const markAsUpdated = useCallback((sessionId: string, data: {
    status: string;
    moodPrompt?: string;
    startedAt?: string;
  }) => {
    logger.debug('Marking workflow as updated', { 
      component: 'useWorkflowEvents', 
      sessionId,
      status: data.status
    });
    workflowEvents.updated({
      sessionId,
      ...data,
    });
  }, []);

  return {
    markAsRemoved,
    markAsUpdated,
  };
}
```

### Benefits
- ✅ Encapsulation: Event logic centralized
- ✅ Logging: Consistent event logging
- ✅ Testability: Easy to mock events
- ✅ Maintainability: Change event format once

---

## 10. Component Composition: Split Large Components

### Current State
Some components like `CreateSessionPageContent` mix multiple concerns.

### Recommendation
Split into smaller, focused components:

```typescript
// src/components/features/create/CreateSessionContent.tsx
export function CreateSessionContent({ 
  sessionId,
  workflowState,
  onBack 
}: CreateSessionContentProps) {
  if (workflowState.awaitingInput && workflowState.recommendations.length > 0) {
    return (
      <CreateSessionEditor
        sessionId={sessionId}
        recommendations={workflowState.recommendations}
        colorScheme={workflowState.moodAnalysis?.color_scheme}
        onBack={onBack}
      />
    );
  }

  if (isTerminalStatus(workflowState.status) && workflowState.recommendations.length === 0) {
    return (
      <CreateSessionError
        colorScheme={workflowState.moodAnalysis?.color_scheme}
        error={workflowState.error}
        onBack={onBack}
      />
    );
  }

  return (
    <CreateSessionProgress
      sessionId={sessionId}
      status={workflowState.status}
      colorScheme={workflowState.moodAnalysis?.color_scheme}
      onBack={onBack}
    />
  );
}
```

### Benefits
- ✅ Readability: Clear component boundaries
- ✅ Reusability: Components can be used independently
- ✅ Testability: Test each component in isolation
- ✅ Maintainability: Easier to understand and modify

---

## Priority Recommendations

### High Priority (Immediate Impact)
1. **Config Type Definitions** - Quick win, improves DX immediately
2. **Use Existing useDebouncedSearch** - Removes duplicate code
3. **Consistent Utility Usage** - Improves code quality
4. **Extract Error Handling** - Reduces boilerplate

### Medium Priority (Architectural Improvements)
5. **AuthContext Refactoring** - Improves testability and separation
6. **Navigation Hook Extraction** - Cleaner components
7. **Simplify Loading State** - Better performance

### Low Priority (Nice to Have)
8. **Workflow Events Hook** - Better encapsulation
9. **Component Composition** - Long-term maintainability

---

## Implementation Guidelines

### General Principles
1. **Preserve Workspace Context**: All refactoring must maintain the AI playlist generation workflow
2. **Incremental Changes**: Implement one refactoring at a time
3. **Test After Each Change**: Ensure functionality remains intact
4. **Update Documentation**: Keep README and comments current
5. **Maintain Backward Compatibility**: Don't break existing features

### Testing Strategy
- Unit test extracted hooks and utilities
- Integration test refactored contexts
- E2E test critical workflows (create playlist, edit, save)
- Manual test on mobile devices for touch interactions

### Code Review Checklist
- [ ] Does this preserve existing functionality?
- [ ] Is the refactored code more testable?
- [ ] Does this improve code organization?
- [ ] Are types properly defined?
- [ ] Is error handling consistent?
- [ ] Does this follow existing patterns?

---

## Long-term Architecture Goals

### Future Enhancements
1. **State Management**: Consider Zustand or Jotai if context becomes too complex
2. **API Layer**: Consolidate all API services with shared error handling
3. **Testing**: Increase test coverage for hooks and components
4. **Performance**: Implement React.memo strategically for heavy components
5. **Accessibility**: Ensure all interactive elements are keyboard accessible
6. **Mobile**: Optimize touch interactions and responsive layouts

### Monitoring
- Track bundle size after refactoring
- Monitor Core Web Vitals (LCP, FID, CLS)
- Log errors to identify problem areas
- Track user flow completion rates

---

## Conclusion

These refactoring opportunities maintain the existing MoodList functionality while improving code quality, testability, and developer experience. Each recommendation is designed to work within the current architecture without requiring major rewrites.

The focus is on:
- ✅ Extracting reusable logic into hooks and utilities
- ✅ Separating concerns (UI, state, API, business logic)
- ✅ Improving type safety and IDE support
- ✅ Reducing code duplication
- ✅ Making the codebase more maintainable

Start with high-priority items for quick wins, then progressively work through medium and low-priority improvements as time allows.
