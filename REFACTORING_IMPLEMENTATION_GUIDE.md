# Refactoring Implementation Guide

## Quick Start: High-Priority Refactorings

This guide provides step-by-step instructions for implementing the high-priority refactorings identified in `FRONTEND_REFACTORING_OPPORTUNITIES.md`. Each refactoring is standalone and can be implemented independently.

---

## 1. Add Config Type Definitions

**⏱️ Estimated Time:** 10 minutes  
**🎯 Impact:** Immediate improvement to DX, better type safety  
**⚠️ Risk:** Low (additive change)

### Step-by-Step Implementation

#### 1. Update `src/lib/config.ts`

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
    cacheTTL: 24 * 60 * 60 * 1000, // 24 hours - matches session expiration
  },
  polling: {
    baseInterval: 3000,          // 3s
    maxBackoff: 30000,           // 30s
    maxRetries: 3,
    awaitingInputInterval: 10000, // 10s
    pendingInterval: 5000,        // 5s
  },
};
```

#### 2. Verify TypeScript Errors

```bash
cd frontend
npm run type-check
```

#### 3. Test in IDE

Open any file that imports `config` and verify autocomplete works:
```typescript
import { config } from '@/lib/config';

// Should autocomplete:
config.api.baseUrl
config.auth.cacheTTL
config.polling.maxRetries
```

### Success Criteria
- ✅ TypeScript compiles without errors
- ✅ IDE shows autocomplete for config properties
- ✅ Existing functionality unchanged

---

## 2. Use Existing useDebouncedSearch Hook

**⏱️ Estimated Time:** 30 minutes  
**🎯 Impact:** Remove duplicate code, improve maintainability  
**⚠️ Risk:** Low (replacing with tested hook)

### Step-by-Step Implementation

#### 1. Review Current Implementation

```bash
# Current file with duplicate logic
frontend/src/lib/hooks/playlist/usePlaylistEdits.ts (lines 137-184)

# Existing reusable hook
frontend/src/lib/hooks/ui/useDebouncedSearch.ts
```

#### 2. Update `src/lib/hooks/playlist/usePlaylistEdits.ts`

Replace lines 33-41 with:
```typescript
import { useDebouncedSearch } from '../ui/useDebouncedSearch';

// Remove these lines:
// const [searchQuery, setSearchQuery] = useState('');
// const [isSearchPending, setIsSearchPending] = useState(false);
// const latestSearchQueryRef = useRef<string>('');
// const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

// Add this instead:
const [searchQuery, setSearchQuery, debouncedQuery] = useDebouncedSearch('', undefined, 300);
```

#### 3. Update Search Effect

Replace the `searchTracks` function (lines 137-184) with:
```typescript
// Calculate pending state
const isSearchPending = searchQuery !== debouncedQuery;

// Effect to perform search when debounced query changes
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
```

#### 4. Remove Cleanup Effect

Delete lines 48-55 (cleanup of searchTimeoutRef):
```typescript
// DELETE THIS:
// useEffect(() => {
//   return () => {
//     if (searchTimeoutRef.current) {
//       clearTimeout(searchTimeoutRef.current);
//     }
//   };
// }, []);
```

#### 5. Update Return Value

Change the return statement:
```typescript
return {
  // ... other returns ...
  searchQuery,
  searchResults,
  isSearching,
  isSearchPending,
  searchTracks: setSearchQuery, // Simplified interface
};
```

#### 6. Test Search Functionality

```bash
# Start dev server
npm run dev

# Test in browser:
# 1. Go to /playlist/[id]/edit
# 2. Type in search box
# 3. Verify debouncing works (300ms delay)
# 4. Verify search results appear
# 5. Type quickly - should not trigger multiple searches
```

### Success Criteria
- ✅ Search still works with 300ms debounce
- ✅ No duplicate searches when typing quickly
- ✅ Loading indicators work correctly
- ✅ Code is simpler and more maintainable

---

## 3. Extract API Error Handling Utility

**⏱️ Estimated Time:** 20 minutes  
**🎯 Impact:** Reduce boilerplate, improve consistency  
**⚠️ Risk:** Low (new utility function)

### Step-by-Step Implementation

#### 1. Create `src/lib/utils/apiErrorHandling.ts`

```typescript
// src/lib/utils/apiErrorHandling.ts
/**
 * Extract user-friendly error message from API response
 */
export async function extractErrorMessage(response: Response): Promise<string> {
  const defaultMessage = `Request failed: ${response.status} ${response.statusText}`;
  
  try {
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      return defaultMessage;
    }

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

    // Array of validation errors
    if (Array.isArray(errorData.detail)) {
      return errorData.detail.map((e: any) => e.msg).join(', ');
    }
  } catch {
    // If parsing fails, use default message
  }
  
  return defaultMessage;
}

/**
 * Standardized API error class
 */
export class APIError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly endpoint?: string
  ) {
    super(message);
    this.name = 'APIError';
  }

  /**
   * Check if error is a specific HTTP status
   */
  isStatus(status: number): boolean {
    return this.status === status;
  }

  /**
   * Check if error is a client error (4xx)
   */
  isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /**
   * Check if error is a server error (5xx)
   */
  isServerError(): boolean {
    return this.status >= 500 && this.status < 600;
  }
}
```

#### 2. Update `src/lib/api/workflow.ts`

Replace the WorkflowAPIError class (lines 128-133):
```typescript
// DELETE THIS:
// class WorkflowAPIError extends Error {
//   constructor(public status: number, message: string) {
//     super(message);
//     this.name = 'WorkflowAPIError';
//   }
// }

// ADD THIS IMPORT AT TOP:
import { extractErrorMessage, APIError } from '@/lib/utils/apiErrorHandling';
```

Update the request method (lines 156-175):
```typescript
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

Update error handling in hooks to use new APIError:
```typescript
// Before:
catch (error) {
  if (error instanceof WorkflowAPIError) {
    // ...
  }
}

// After:
catch (error) {
  if (error instanceof APIError) {
    if (error.isStatus(429)) {
      showError('Rate limit exceeded. Please try again later.');
    } else if (error.isClientError()) {
      showError(error.message);
    } else {
      showError('Server error. Please try again.');
    }
  }
}
```

#### 3. Update Other API Services

Apply the same pattern to `src/lib/api/auth.ts` if needed.

#### 4. Test Error Handling

```bash
# Test various error scenarios:
# 1. Network error (disconnect internet)
# 2. 401 Unauthorized (logout and try protected endpoint)
# 3. 429 Rate limit (make many rapid requests)
# 4. 500 Server error (trigger backend error)
```

### Success Criteria
- ✅ Error messages are user-friendly
- ✅ Different error types handled appropriately
- ✅ Error extraction works for all API response formats
- ✅ Code is more maintainable

---

## 4. Consistent Workflow Status Utilities

**⏱️ Estimated Time:** 15 minutes  
**🎯 Impact:** Improve consistency, reduce duplication  
**⚠️ Risk:** Very Low (pure functions)

### Step-by-Step Implementation

#### 1. Update `src/lib/utils/workflow.ts`

Add these utility functions:
```typescript
/**
 * Checks if a workflow status is in a terminal state
 */
export function isTerminalStatus(status: string | null): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled';
}

/**
 * Checks if a workflow is actively running (not terminal)
 */
export function isActiveStatus(status: string | null): boolean {
  return status !== null && !isTerminalStatus(status);
}

/**
 * Checks if a workflow ended in an error state
 */
export function isErrorStatus(status: string | null): boolean {
  return status === 'failed' || status === 'cancelled';
}

/**
 * Checks if a workflow completed successfully
 */
export function isSuccessStatus(status: string | null): boolean {
  return status === 'completed';
}

/**
 * Get user-friendly status message
 */
export function getStatusMessage(status: string | null, currentStep?: string): string {
  if (!status) return 'Initializing...';
  
  const messages: Record<string, string> = {
    pending: 'Starting workflow...',
    analyzing_mood: 'Analyzing your mood...',
    gathering_seeds: 'Finding seed tracks...',
    generating_recommendations: 'Generating recommendations...',
    evaluating_quality: 'Evaluating track quality...',
    optimizing_recommendations: 'Optimizing playlist...',
    ordering_playlist: 'Ordering tracks...',
    awaiting_user_input: 'Awaiting your input...',
    processing_edits: 'Processing your edits...',
    creating_playlist: 'Creating playlist...',
    completed: 'Playlist completed!',
    failed: 'Workflow failed',
    cancelled: 'Workflow cancelled',
  };

  return messages[status] || currentStep || status;
}
```

#### 2. Find and Replace Inline Status Checks

Search for inline status checks:
```bash
cd frontend/src
# Find inline terminal status checks
grep -r "status === 'completed' || status === 'failed'" .

# Find inline active checks
grep -r "status !== null && status !== 'completed'" .
```

#### 3. Update Components

Example in `src/app/create/[id]/page.tsx`:

Before:
```typescript
const isActive = workflowState.status !== 'completed' && 
                 workflowState.status !== 'failed' && 
                 workflowState.status !== 'cancelled';

const isTerminalStatus = workflowState.status === 'completed' || 
                        workflowState.status === 'failed' || 
                        workflowState.status === 'cancelled';
```

After:
```typescript
import { isActiveStatus, isTerminalStatus } from '@/lib/utils/workflow';

const isActive = isActiveStatus(workflowState.status);
const isTerminal = isTerminalStatus(workflowState.status);
```

#### 4. Update All Files

Update these files (search for inline checks):
- `src/app/create/[id]/page.tsx`
- `src/components/features/workflow/WorkflowProgress.tsx`
- `src/components/features/workflow/StatusIcon.tsx`
- `src/lib/hooks/workflow/useWorkflowState.ts`

#### 5. Test Status Checks

```bash
# Run type check
npm run type-check

# Run dev server and test workflows
npm run dev

# Test scenarios:
# 1. Create new playlist (pending → completed)
# 2. Cancel workflow (active → cancelled)
# 3. Trigger error (active → failed)
```

### Success Criteria
- ✅ All inline status checks replaced
- ✅ Consistent behavior across components
- ✅ TypeScript compiles without errors
- ✅ All workflow states handled correctly

---

## 5. Extract Auth Cache Management Hook

**⏱️ Estimated Time:** 45 minutes  
**🎯 Impact:** Better separation of concerns, improved testability  
**⚠️ Risk:** Medium (touches critical auth flow)

### Step-by-Step Implementation

#### 1. Create `src/lib/hooks/auth/useAuthCache.ts`

```typescript
// src/lib/hooks/auth/useAuthCache.ts
import { useCallback } from 'react';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import type { User, CachedAuthData } from '@/lib/types/auth';

/**
 * Hook for managing authentication cache in sessionStorage
 */
export function useAuthCache() {
  const getCachedAuth = useCallback((): CachedAuthData | null => {
    if (typeof window === 'undefined') return null;
    
    try {
      const cached = sessionStorage.getItem(config.auth.cacheKey);
      if (!cached) return null;

      const data: CachedAuthData = JSON.parse(cached);
      const age = Date.now() - data.timestamp;

      // Check if cache is still valid (within TTL)
      if (age > config.auth.cacheTTL) {
        sessionStorage.removeItem(config.auth.cacheKey);
        return null;
      }

      return data;
    } catch (error) {
      logger.warn('Failed to read auth cache', { component: 'useAuthCache', error });
      return null;
    }
  }, []);

  const setCachedAuth = useCallback((user: User): void => {
    if (typeof window === 'undefined') return;
    
    try {
      const data: CachedAuthData = {
        user,
        timestamp: Date.now(),
      };
      sessionStorage.setItem(config.auth.cacheKey, JSON.stringify(data));
      logger.debug('Auth cache updated', { component: 'useAuthCache', userId: user.id });
    } catch (error) {
      logger.warn('Failed to write auth cache', { component: 'useAuthCache', error });
    }
  }, []);

  const clearCachedAuth = useCallback((): void => {
    if (typeof window === 'undefined') return;
    
    try {
      sessionStorage.removeItem(config.auth.cacheKey);
      logger.debug('Auth cache cleared', { component: 'useAuthCache' });
    } catch (error) {
      logger.warn('Failed to clear auth cache', { component: 'useAuthCache', error });
    }
  }, []);

  return {
    getCachedAuth,
    setCachedAuth,
    clearCachedAuth,
  };
}
```

#### 2. Update `src/lib/hooks/auth/index.ts`

```typescript
// src/lib/hooks/auth/index.ts
export * from './useAuthCache';
// ... other exports
```

#### 3. Update `src/lib/contexts/AuthContext.tsx`

Replace lines 18-62 with:
```typescript
import { useAuthCache } from '@/lib/hooks/auth/useAuthCache';

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isValidated, setIsValidated] = useState(false);

  // Use the extracted cache hook
  const { getCachedAuth, setCachedAuth, clearCachedAuth } = useAuthCache();

  // ... rest of the component
```

Update all cache operations to use the hook methods:
- `getCachedAuth()` instead of inline cache reading
- `setCachedAuth(user)` instead of inline cache writing  
- `clearCachedAuth()` instead of inline cache clearing

#### 4. Test Auth Flow

```bash
# Start dev server
npm run dev

# Test scenarios:
# 1. Fresh login - verify cache is created
# 2. Page refresh - verify cache is used
# 3. Logout - verify cache is cleared
# 4. Cache expiry - verify old cache is ignored

# Check browser console for cache logs
# Check sessionStorage in DevTools
```

#### 5. Write Unit Tests (Optional)

```typescript
// src/lib/hooks/auth/__tests__/useAuthCache.test.ts
import { renderHook } from '@testing-library/react';
import { useAuthCache } from '../useAuthCache';

describe('useAuthCache', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('should return null when no cache exists', () => {
    const { result } = renderHook(() => useAuthCache());
    expect(result.current.getCachedAuth()).toBeNull();
  });

  it('should cache and retrieve user data', () => {
    const { result } = renderHook(() => useAuthCache());
    const mockUser = { id: '123', display_name: 'Test User' };

    result.current.setCachedAuth(mockUser);
    const cached = result.current.getCachedAuth();

    expect(cached?.user).toEqual(mockUser);
  });

  it('should clear cache', () => {
    const { result } = renderHook(() => useAuthCache());
    const mockUser = { id: '123', display_name: 'Test User' };

    result.current.setCachedAuth(mockUser);
    result.current.clearCachedAuth();
    
    expect(result.current.getCachedAuth()).toBeNull();
  });
});
```

### Success Criteria
- ✅ Cache operations extracted to hook
- ✅ Auth flow still works correctly
- ✅ Cache TTL respected
- ✅ Logout clears cache
- ✅ Unit tests pass (if written)

---

## Testing Checklist

After each refactoring, verify:

### Functional Testing
- [ ] Authentication flow works
- [ ] Workflow creation succeeds
- [ ] Playlist editing works
- [ ] Search functionality intact
- [ ] Error messages display correctly
- [ ] Loading states show properly

### Technical Testing
- [ ] TypeScript compiles without errors
- [ ] ESLint passes
- [ ] No console errors
- [ ] No console warnings (except known issues)
- [ ] Network requests unchanged
- [ ] Performance not degraded

### Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

---

## Rollback Procedures

If any refactoring causes issues:

### Quick Rollback
```bash
# Discard changes to a specific file
git checkout -- path/to/file.ts

# Discard all uncommitted changes
git reset --hard HEAD
```

### Partial Rollback
```bash
# Stash current changes
git stash

# Test without changes
npm run dev

# Restore changes
git stash pop
```

### Commit Rollback
```bash
# Revert a specific commit
git revert <commit-hash>

# Reset to previous commit (dangerous!)
git reset --hard HEAD~1
```

---

## Performance Monitoring

Track these metrics before/after refactoring:

### Bundle Size
```bash
npm run build
# Check .next/analyze or bundle size report
```

### Lighthouse Scores
```bash
npx lighthouse http://localhost:3000 --view
```

### Key Metrics
- **FCP** (First Contentful Paint): < 1.8s
- **LCP** (Largest Contentful Paint): < 2.5s
- **TBT** (Total Blocking Time): < 300ms
- **CLS** (Cumulative Layout Shift): < 0.1

---

## Next Steps

After completing high-priority refactorings:

1. **Review**: Code review with team
2. **Document**: Update inline comments
3. **Test**: Comprehensive QA testing
4. **Deploy**: Staging environment first
5. **Monitor**: Watch error rates and performance
6. **Medium Priority**: Move to medium-priority refactorings
7. **Iterate**: Continuously improve based on feedback

---

## Getting Help

If you encounter issues:

1. **Check Logs**: Browser console and backend logs
2. **Review Docs**: `FRONTEND_REFACTORING_OPPORTUNITIES.md`
3. **Compare Code**: Look at similar patterns in codebase
4. **Ask Team**: Post in development channel
5. **Create Issue**: Document problem and steps to reproduce

---

## Summary

This guide provides practical, step-by-step instructions for implementing the top refactorings. Each refactoring:

- ✅ Has clear instructions
- ✅ Includes code examples
- ✅ Provides testing steps
- ✅ Offers rollback procedures
- ✅ Maintains workspace context

Start with config types (quickest win), then move through the list based on your available time and confidence level.
