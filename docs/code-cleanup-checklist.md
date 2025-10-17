# Code Cleanup Checklist

This document identifies technical debt and cleanup opportunities discovered during the frontend refactor planning phase.

---

## Priority Issues

### 🔴 Critical: Auth Performance (Phase 2.5)
**Status:** Documented in refactor plan  
**Impact:** High - Affects all protected routes  
**Effort:** Medium (3-5 days)

See Phase 2.5 in `frontend-refactor-plan.md` for complete solution.

---

## Code Quality Issues

### 1. Console Logging Cleanup

**Problem:** Debug `console.log` statements left in production code.

**Files affected:**
- `src/app/create/[id]/page.tsx`
- `src/components/WorkflowProgress.tsx`
- `src/components/PlaylistResults.tsx`
- `src/app/create/page.tsx`
- `src/lib/pollingManager.ts`
- `src/lib/authContext.tsx`
- `src/lib/workflowApi.ts`
- `src/lib/workflowContext.tsx`

**Solution:**
Create a structured logging utility and replace all console logs.

**Implementation:**
```typescript
// lib/utils/logger.ts
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  component?: string;
  action?: string;
  [key: string]: any;
}

class Logger {
  private isDev = process.env.NODE_ENV === 'development';
  
  private log(level: LogLevel, message: string, context?: LogContext) {
    if (!this.isDev && level === 'debug') return;
    
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    const contextStr = context ? ` ${JSON.stringify(context)}` : '';
    
    const fullMessage = `${prefix} ${message}${contextStr}`;
    
    switch (level) {
      case 'error':
        console.error(fullMessage);
        // Send to error tracking service (Sentry, etc.)
        break;
      case 'warn':
        console.warn(fullMessage);
        break;
      case 'info':
        console.info(fullMessage);
        break;
      case 'debug':
        console.log(fullMessage);
        break;
    }
  }
  
  debug(message: string, context?: LogContext) {
    this.log('debug', message, context);
  }
  
  info(message: string, context?: LogContext) {
    this.log('info', message, context);
  }
  
  warn(message: string, context?: LogContext) {
    this.log('warn', message, context);
  }
  
  error(message: string, error?: Error, context?: LogContext) {
    this.log('error', message, {
      ...context,
      error: error?.message,
      stack: error?.stack,
    });
  }
}

export const logger = new Logger();
```

**Usage:**
```typescript
// Before
console.log('Polling already active for session:', sessionId);

// After
logger.debug('Polling already active', { 
  component: 'PollingManager', 
  sessionId 
});
```

**Checklist:**
- [ ] Create `lib/utils/logger.ts`
- [ ] Replace all `console.log` with `logger.debug`
- [ ] Replace all `console.error` with `logger.error`
- [ ] Add component context to all log calls
- [ ] Configure production log filtering
- [ ] Add eslint rule to prevent future console usage

---

### 2. Window.location.reload() Anti-pattern

**Problem:** Using `window.location.reload()` causes full page refreshes, losing state and degrading UX.

**Files affected:**
- `src/app/create/[id]/page.tsx` - 3 occurrences
- `src/components/Navigation.tsx` - 2 occurrences
- `src/app/playlists/page.tsx` - 1 occurrence
- `src/app/create/page.tsx` - 2 occurrences

**Impact:**
- Loss of in-memory state
- Flash of unstyled content
- Unnecessary network requests
- Poor perceived performance

**Solution:**
Replace with proper state management and router navigation.

**Examples:**

**Before:**
```typescript
// Navigation.tsx - After logout
window.location.href = '/';
```

**After:**
```typescript
// Use Next.js router
import { useRouter } from 'next/navigation';

const router = useRouter();
await logout();
router.push('/');
router.refresh(); // Refresh server components if needed
```

**Before:**
```typescript
// create/page.tsx - After edit complete
const handleEditComplete = () => {
  window.location.reload();
};
```

**After:**
```typescript
const handleEditComplete = () => {
  // Trigger state refresh in context
  await refreshResults();
  // Or navigate to results view
  router.push(`/playlist/${sessionId}`);
};
```

**Checklist:**
- [ ] Replace `window.location.reload()` in Navigation.tsx
- [ ] Replace reload in create/page.tsx
- [ ] Replace reload in create/[id]/page.tsx
- [ ] Replace reload in playlists/page.tsx
- [ ] Add proper state invalidation hooks
- [ ] Test state preservation across navigation

---

### 3. Duplicate Loading Indicator Patterns

**Problem:** Multiple inconsistent loading spinner implementations across components.

**Instances found:**
```typescript
// page.tsx - Bouncing dots
<div className="w-4 h-4 bg-primary rounded-full animate-bounce"></div>

// Navigation.tsx - Pulse skeleton
<div className="w-8 h-8 bg-primary/20 rounded-lg animate-pulse"></div>

// Various pages - LoadingDots component
<LoadingDots size="sm" />
```

**Solution:**
Standardize on a single loading component with variants.

**Implementation:**
```typescript
// components/ui/loading.tsx
export type LoadingSize = 'xs' | 'sm' | 'md' | 'lg';
export type LoadingVariant = 'spinner' | 'dots' | 'pulse';

interface LoadingProps {
  size?: LoadingSize;
  variant?: LoadingVariant;
  className?: string;
}

export function Loading({ 
  size = 'md', 
  variant = 'dots',
  className 
}: LoadingProps) {
  // Unified implementation with size/variant support
}
```

**Checklist:**
- [ ] Audit all loading UI instances
- [ ] Create unified Loading component
- [ ] Replace all custom loading implementations
- [ ] Add loading states to design system docs

---

### 4. Environment Variable Duplication

**Problem:** Backend URL repeated in multiple files.

**Pattern:**
```typescript
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
```

**Files affected:**
- `src/lib/authContext.tsx`
- `src/lib/workflowApi.ts`
- `src/lib/playlistApi.ts`
- `src/lib/spotifyAuth.ts` (likely)

**Solution:**
Centralize configuration.

**Implementation:**
```typescript
// lib/config.ts
export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  auth: {
    sessionCookieName: 'session_token',
    cacheKey: 'moodlist_auth_cache',
    cacheTTL: 2 * 60 * 1000, // 2 minutes
  },
  polling: {
    baseInterval: 2000,
    maxBackoff: 30000,
    maxRetries: 3,
  },
} as const;

// Usage
import { config } from '@/lib/config';
const response = await fetch(`${config.api.baseUrl}/auth/verify`);
```

**Checklist:**
- [ ] Create centralized config file
- [ ] Replace all hardcoded URLs
- [ ] Replace all magic numbers with config values
- [ ] Document environment variables in README
- [ ] Add config validation on startup

---

### 5. Inconsistent Error Handling

**Problem:** Error handling patterns vary across the codebase.

**Current patterns:**
```typescript
// Pattern 1: Silent catch
try {
  await action();
} catch (error) {
  console.error('Error:', error);
}

// Pattern 2: Generic error message
catch (err) {
  const errorMessage = err instanceof Error ? err.message : 'Failed';
  setError(errorMessage);
}

// Pattern 3: Toast notification
catch (error) {
  toast.error('Action failed');
}
```

**Solution:**
Create unified error handling utilities.

**Implementation:**
```typescript
// lib/utils/errors.ts
export class AppError extends Error {
  constructor(
    message: string,
    public code?: string,
    public status?: number,
    public context?: Record<string, any>
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export function handleApiError(error: unknown): AppError {
  if (error instanceof AppError) {
    return error;
  }
  
  if (error instanceof Response) {
    return new AppError(
      `Request failed: ${error.statusText}`,
      'API_ERROR',
      error.status
    );
  }
  
  if (error instanceof Error) {
    return new AppError(error.message, 'UNKNOWN_ERROR');
  }
  
  return new AppError('An unexpected error occurred', 'UNKNOWN_ERROR');
}

export function getUserFriendlyMessage(error: AppError): string {
  switch (error.code) {
    case 'NETWORK_ERROR':
      return 'Network connection issue. Please check your internet.';
    case 'AUTH_ERROR':
      return 'Your session has expired. Please log in again.';
    case 'RATE_LIMIT':
      return 'Too many requests. Please wait a moment and try again.';
    default:
      return error.message || 'Something went wrong. Please try again.';
  }
}
```

**Usage:**
```typescript
try {
  await action();
} catch (error) {
  const appError = handleApiError(error);
  logger.error('Action failed', appError, { component: 'MyComponent' });
  
  const userMessage = getUserFriendlyMessage(appError);
  toast.error(userMessage);
  
  setError(appError);
}
```

**Checklist:**
- [ ] Create error utility classes
- [ ] Define error codes enum
- [ ] Map error codes to user messages
- [ ] Replace all error handling with utilities
- [ ] Add error boundaries for unhandled errors

---

### 6. TypeScript Type Safety Gaps

**Problem:** Loose typing in several areas.

**Issues found:**

**Generic `any` in polling callbacks:**
```typescript
// pollingManager.ts
onStatus: (status: any) => void;
```

**Solution:**
```typescript
interface WorkflowStatus {
  session_id: string;
  status: 'pending' | 'analyzing_mood' | 'completed' | 'failed';
  current_step: string;
  awaiting_input: boolean;
  error?: string;
}

onStatus: (status: WorkflowStatus) => void;
```

**Untyped playlist data:**
```typescript
// Various components
const [playlists, setPlaylists] = useState<any[]>([]);
```

**Solution:**
```typescript
interface Playlist {
  id: number;
  mood_prompt: string;
  name: string | null;
  track_count: number;
  status: 'completed' | 'pending';
  created_at: string;
  spotify_url?: string;
  // ... other fields
}

const [playlists, setPlaylists] = useState<Playlist[]>([]);
```

**Checklist:**
- [ ] Audit all `any` types
- [ ] Create shared type definitions file
- [ ] Enable `strict` mode in tsconfig
- [ ] Add `@typescript-eslint/no-explicit-any` rule
- [ ] Create types for all API responses

---

### 7. Magic Numbers and Strings

**Problem:** Hardcoded values scattered throughout code.

**Examples:**
```typescript
// Polling intervals
setTimeout(() => {}, 2000);
setTimeout(() => {}, 5000);

// Cache TTL
const age = Date.now() - data.timestamp;
if (age > 120000) { } // What is 120000?

// Route paths
if (pathname.startsWith('/create')) { }
if (pathname.startsWith('/playlists')) { }
```

**Solution:**
Centralize as constants.

**Implementation:**
```typescript
// lib/constants.ts
export const ROUTES = {
  HOME: '/',
  CREATE: '/create',
  PLAYLISTS: '/playlists',
  PLAYLIST: '/playlist',
  PROFILE: '/profile',
  CALLBACK: '/callback',
  ABOUT: '/about',
} as const;

export const TIMING = {
  POLLING_INTERVAL: 2000,
  POLLING_INTERVAL_WAITING: 5000,
  AUTH_CACHE_TTL: 2 * 60 * 1000,
  TOAST_DURATION: 3000,
  ANIMATION_DELAY: 100,
} as const;

export const COOKIES = {
  SESSION_TOKEN: 'session_token',
} as const;
```

**Usage:**
```typescript
import { ROUTES, TIMING, COOKIES } from '@/lib/constants';

if (pathname.startsWith(ROUTES.CREATE)) { }
setTimeout(poll, TIMING.POLLING_INTERVAL);
const cookie = getCookie(COOKIES.SESSION_TOKEN);
```

**Checklist:**
- [ ] Extract all magic numbers
- [ ] Extract all magic strings
- [ ] Create constants file
- [ ] Update all references
- [ ] Document constant meanings

---

## Component-Specific Issues

### 8. Navigation Component Complexity

**Metrics:**
- Lines: 290
- State variables: 4+
- Nested conditionals: Multiple levels
- Responsibilities: Auth, mobile menu, theme, routing

**Recommendation:** Split into smaller components (documented in Phase 3).

---

### 9. PlaylistEditor Component Complexity

**Metrics:**
- Lines: 624
- DnD logic mixed with UI
- Search, edit, save all in one file

**Recommendation:** Extract into subcomponents (documented in Phase 3).

---

### 10. WorkflowContext Overloaded

**Metrics:**
- Lines: 607
- Responsibilities: Start, load, stop, reset, edit, search, save, sync

**Recommendation:** Split responsibilities (documented in Phase 3).

---

## Testing Gaps

### 11. Missing Unit Tests

**Coverage:** ~0%

**Priority areas needing tests:**
- [ ] Authentication flow (login, logout, verification)
- [ ] Workflow state management
- [ ] Playlist editing logic
- [ ] Utility functions (moodColors, validation)
- [ ] API clients (error handling, retries)

---

### 12. Missing Integration Tests

**Recommended flows:**
- [ ] Complete playlist creation flow
- [ ] Edit existing playlist flow
- [ ] Login/logout flow
- [ ] Refresh/navigation flows

---

## Documentation Gaps

### 13. Component Documentation

**Missing:**
- [ ] PropTypes JSDoc comments
- [ ] Component usage examples
- [ ] State management explanations
- [ ] Hook parameter documentation

**Example:**
```typescript
/**
 * Displays workflow progress with real-time status updates.
 * 
 * @param sessionId - The workflow session identifier
 * @param onComplete - Callback when workflow reaches terminal state
 * @param onError - Callback when workflow encounters an error
 * 
 * @example
 * ```tsx
 * <WorkflowProgress 
 *   sessionId="abc123"
 *   onComplete={() => router.push('/results')}
 * />
 * ```
 */
export function WorkflowProgress({ sessionId, onComplete, onError }: Props) {
  // ...
}
```

---

### 14. README Updates Needed

**Missing documentation:**
- [ ] Environment variables reference
- [ ] Development setup instructions
- [ ] Architecture overview
- [ ] Testing instructions
- [ ] Deployment guide
- [ ] Troubleshooting section

---

## Performance Issues

### 15. Unnecessary Re-renders

**Problem:** Context consumers re-render on any state change.

**Example:**
```typescript
// AuthContext updates cause all consumers to re-render
const { user, isLoading, isAuthenticated } = useAuth();
```

**Solution:** Split contexts or use selectors.

```typescript
// Split into AuthUserContext and AuthStatusContext
const user = useAuthUser(); // Only re-renders on user change
const isAuthenticated = useAuthStatus(); // Only re-renders on status change
```

**Checklist:**
- [ ] Audit context re-render frequency
- [ ] Split large contexts
- [ ] Memoize expensive computations
- [ ] Add React.memo where appropriate

---

### 16. Missing Code Splitting

**Problem:** All route code bundled together.

**Solution:** Use dynamic imports for heavy features.

```typescript
// Lazy load DnD editor
const PlaylistEditor = dynamic(() => import('@/components/PlaylistEditor'), {
  loading: () => <EditorSkeleton />,
  ssr: false,
});
```

**Checklist:**
- [ ] Identify heavy dependencies (DnD, animations)
- [ ] Lazy load non-critical features
- [ ] Add loading skeletons
- [ ] Measure bundle size improvements

---

## Security Considerations

### 17. Client-Side Secret Exposure

**Audit:** Ensure no sensitive keys in client code.

**Checklist:**
- [ ] Review all `NEXT_PUBLIC_*` env vars
- [ ] Confirm API keys are server-side only
- [ ] Add `.env.example` with safe defaults
- [ ] Document which vars can be public

---

### 18. XSS Prevention

**Check:** Sanitize user input in mood descriptions.

**Current:** Using React (auto-escapes by default) ✅

**Verify:**
- [ ] No `dangerouslySetInnerHTML` usage
- [ ] No direct DOM manipulation
- [ ] User content displayed through React components

---

## Quick Wins (Low Effort, High Impact)

1. **Add .env.example** - 5 minutes
2. **Create constants.ts** - 30 minutes
3. **Unified logger** - 1 hour
4. **Remove console.logs** - 1 hour
5. **Type polling callbacks** - 30 minutes
6. **Centralize config** - 1 hour
7. **Update README** - 2 hours

**Total:** ~1 day of work for significant quality improvements

---

## Cleanup Implementation Order

### Week 1: Foundation
1. Create logger utility
2. Create error handling utilities
3. Create constants file
4. Create centralized config
5. Update README

### Week 2: Code Quality
6. Replace all console.logs
7. Remove window.location.reload
8. Fix environment variable duplication
9. Standardize loading indicators
10. Improve TypeScript strictness

### Week 3: Testing & Docs
11. Add component JSDoc comments
12. Write unit tests for utilities
13. Add integration tests for critical flows
14. Update architecture documentation

### Week 4: Performance
15. Audit and fix re-render issues
16. Implement code splitting
17. Add performance monitoring
18. Measure and document improvements

---

## Success Metrics

Track these to measure cleanup progress:

| Metric | Current | Target |
|--------|---------|--------|
| Console.log count | 8+ files | 0 |
| window.reload count | 4 files | 0 |
| Test coverage | ~0% | >50% |
| TypeScript `any` count | Multiple | Minimal |
| Lines per component (avg) | 300+ | <200 |
| Bundle size (gzipped) | TBD | -15% |
| Lighthouse score | TBD | >90 |

---

This checklist should be revisited quarterly and updated as new technical debt is identified.
