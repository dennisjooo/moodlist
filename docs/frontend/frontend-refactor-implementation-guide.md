# Frontend Refactor Implementation Guide

Companion to the main refactoring plan, this guide provides technical implementation details, example patterns, and code snippets for each phase.

---

## Phase 1: Implementation Details

### Phase 1 progress update (branch: refactor/frontend-phase-1)

Date: 2025-10-20

What changed in codebase during Phase 1 cleanup baseline:
- Centralized configuration
  - Added `src/lib/config.ts` with `api.baseUrl`, `auth`, and `polling` settings
  - Added `src/lib/constants.ts` with `ROUTES`, `TIMING`, and `COOKIES` for future use
- Logging standardization
  - Added `src/lib/utils/logger.ts` and began replacing `console.*` calls with structured `logger` usage
  - `logger.debug` is suppressed in production; use `logger.info/warn/error` for important events
- API client hardening
  - Updated `src/lib/workflowApi.ts` and `src/lib/playlistApi.ts` to use `config.api.baseUrl`
  - Standardized request init as `reqConfig` and enforced `credentials: 'include'`
  - Added structured request/response/error logging via `logger`
- Polling strategy configuration
  - Updated `src/lib/pollingManager.ts` to source intervals/backoff from `config.polling` and use `logger`
- Auth flow incremental hygiene (prep for Phase 2.5)
  - Updated `src/lib/authContext.tsx` to use `config.api.baseUrl` and structured logging
- Misc client updates
  - Updated `src/components/SocialProof.tsx` and `src/app/profile/page.tsx` to use `config.api.baseUrl` + `logger`

What is NOT done yet (planned next steps):
- Phase 2.5 critical auth optimizations (optimistic auth provider state machine, `middleware.ts`, and `<AuthGuard>`) remain TODO
- Finish replacing all `console.*` calls across the app (search with grep and convert to `logger`)
- Replace `window.location.reload()` patterns with router navigation/state updates
- Introduce a unified Loading UI and replace ad-hoc spinners

Usage guidelines introduced by these changes:
- Prefer `config.api.baseUrl` over inline `process.env` lookups
- Use the `logger` for all diagnostics: `logger.debug/info/warn/error` with a `component` context
- Pull reusable values from `constants.ts` (`ROUTES`/`TIMING`/`COOKIES`) instead of magic strings/numbers

Touched files in this pass:
- New: `src/lib/config.ts`, `src/lib/constants.ts`, `src/lib/utils/logger.ts`
- Updated: `src/lib/workflowApi.ts`, `src/lib/playlistApi.ts`, `src/lib/pollingManager.ts`, `src/lib/authContext.tsx`
- Updated: `src/components/SocialProof.tsx`, `src/app/profile/page.tsx`

Impact:
- No user-visible behavior changes expected; groundwork laid for Phase 2.5 and later phases (single source of truth for URLs/timing, structured logging).

### Phase 2 progress update (branch: refactor/continue-frontend-docs)

Date: 2025-10-20

What changed in codebase during Phase 2 (architecture + auth lifecycle refinements):
- Auth lifecycle and route protection
  - Added `frontend/middleware.ts` with server-side cookie checks on protected routes (`/create/*`, `/playlists`, `/playlist/*`, `/profile`), intentionally leaving `/create` public per UX
  - Built `<AuthGuard>` at `src/components/auth/AuthGuard.tsx` and wrapped protected pages (`/playlists`, `/playlist/[id]`, `/playlist/[id]/edit`, `/create/[id]`, `/profile`)
  - Upgraded `src/lib/authContext.tsx` to an optimistic, cookie-driven state machine with background verification, sessionStorage caching (2 min TTL), and `auth-validated`/`auth-expired` events
- DX and hooks
  - Added shared hooks: `useDebounce` and `useLocalStorage` under `src/lib/hooks`
  - Refactored `PlaylistEditor` search to use `useDebounce` for clearer, testable logic
- UX hygiene
  - Replaced `window.location.reload()` usages with router navigation/state refresh in Create and Playlist pages; Navigation logout now uses `router.push('/')` + `router.refresh()`
  - Home page now reads `?auth=required|expired` and surfaces user-friendly toasts

What is NOT done yet (remaining Phase 2 items):
- Component taxonomy and folder structure
  - Navigation decomposition into `layout/Navigation/*` is partially implemented (file relocated under layout with re-export); subcomponents/hooks extraction still pending
  - No broader feature folder migration (`components/features/*`) yet; this is planned for Phase 3
- Contexts and state ownership
  - Contexts have been migrated to `src/lib/contexts/*` and imports updated
  - State boundary enforcement (server vs client components) is documented but not yet applied
- Data fetching strategy
  - No adoption of server actions or TanStack Query; current API clients remain
- UI primitives
  - Unified `Loading` component introduced at `src/components/ui/loading.tsx`; rollout to replace ad-hoc loaders will proceed incrementally

Next steps recommended for Phase 2 completion:
1) Decompose `Navigation` into subcomponents and colocate simple hooks (e.g., `useDropdown`, `useMobileNav`)
2) Establish `components/features/*` folders incrementally for auth, mood, workflow, and playlist
3) Draft a minimal data-fetching decision doc and tag candidates for server components
4) Replace scattered loaders with the new `Loading` primitive across pages/components

### 1.1 Component Complexity Scoring

**Current large components identified:**
- `Navigation.tsx` (290 lines) - Mixed presentation/logic, mobile/desktop state
- `PlaylistEditor.tsx` (624 lines) - DnD, search, Spotify sync, form state
- `WorkflowProgress.tsx` (17872 lines noted in earlier inventory) - Likely status polling UI
- `workflowContext.tsx` (607 lines) - Provider with multiple responsibilities

**Scoring criteria:**
```typescript
interface ComponentComplexity {
  lines: number;
  stateVariables: number;
  effects: number;
  externalDependencies: string[];
  cyclomaticComplexity: number;
  testability: 'easy' | 'moderate' | 'hard';
}
```

### 1.2 Dependency Mapping

**Current tech stack:**
- **Core:** Next.js 15.5.3, React 19.1.0, TypeScript 5
- **Styling:** Tailwind CSS v4, Framer Motion, tw-animate-css
- **UI:** Radix primitives, Lucide icons, Sonner toasts
- **DnD:** @dnd-kit
- **State:** React Context (no Zustand/Redux/TanStack Query yet)

**Routing structure:**
```
/                     → Marketing page
/about               → Feature explanations
/create              → Mood input (clean state)
/create/[id]         → Workflow progress + results
/playlist/[id]       → View saved playlist
/playlist/[id]/edit  → Edit existing playlist
/playlists           → List user playlists
/profile             → User account details
/callback            → Spotify OAuth return
```

### 1.3 Performance Baseline Script

```bash
# Bundle size analysis
npm run build -- --profile
npx @next/bundle-analyzer

# Runtime profiling steps
# 1. Open React DevTools Profiler
# 2. Record /create → submit → results flow
# 3. Export timing JSON
# 4. Save to docs/metrics/baseline-YYYY-MM-DD.json

# Lighthouse baseline
npx lighthouse http://localhost:3000 \
  --output=json \
  --output-path=docs/metrics/lighthouse-home-baseline.json
```

---

## Phase 2: Component Architecture Design

### 2.1 Component Folder Structure (Proposed → initial adoption in this branch)

```
src/
├── components/
│   ├── layout/              # App-wide scaffolding
│   │   ├── Navigation/
│   │   │   ├── Navigation.tsx
│   │   │   ├── Brand.tsx
│   │   │   ├── DesktopLinks.tsx
│   │   │   ├── MobileMenu.tsx
│   │   │   └── AuthMenu.tsx
│   │   └── Footer.tsx
│   │
│   ├── features/            # Business logic components
│   │   ├── auth/
│   │   │   ├── LoginDialog.tsx
│   │   │   ├── SpotifyButton.tsx
│   │   │   └── useAuthGuard.ts
│   │   ├── mood/
│   │   │   ├── MoodInput.tsx
│   │   │   ├── MoodCard.tsx
│   │   │   └── PopularMoods.tsx
│   │   ├── workflow/
│   │   │   ├── WorkflowProgress.tsx
│   │   │   ├── MoodAnalysisCard.tsx
│   │   │   └── useWorkflowPolling.ts
│   │   └── playlist/
│   │       ├── PlaylistEditor/
│   │       │   ├── PlaylistEditor.tsx
│   │       │   ├── TrackList.tsx
│   │       │   ├── TrackItem.tsx
│   │       │   ├── TrackSearch.tsx
│   │       │   └── usePlaylistEdits.ts
│   │       ├── PlaylistResults.tsx
│   │       └── PlaylistCard.tsx
│   │
│   ├── marketing/           # Landing & static pages
│   │   ├── HeroSection.tsx
│   │   ├── FeaturesSection.tsx
│   │   ├── SocialProof.tsx
│   │   └── TypewriterText.tsx
│   │
│   └── ui/                  # Primitives (keep existing structure)
│       └── ...
│
├── lib/
│   ├── contexts/            # Renamed for clarity
│   │   ├── AuthContext.tsx
│   │   └── WorkflowContext.tsx
│   ├── hooks/               # Shared hooks
│   │   ├── useLocalStorage.ts
│   │   ├── useDebounce.ts
│   │   └── useToast.ts
│   ├── api/                 # Typed API clients
│   │   ├── workflow.ts
│   │   ├── playlist.ts
│   │   └── spotify.ts
│   └── utils/               # Pure helpers
│       ├── cn.ts
│       ├── colors.ts
│       └── validation.ts
```

### 2.2 Component Contracts

**Example: Navigation prop API**
```typescript
// navigation/Navigation.tsx
export interface NavigationProps {
  /** Optional override for branding link */
  logoHref?: string;
  /** Extra nav items beyond defaults */
  extraItems?: NavItem[];
  /** Callback when user initiates logout */
  onLogout?: () => void;
}

// navigation/AuthMenu.tsx
export interface AuthMenuProps {
  user: User;
  isDropdownOpen: boolean;
  onToggle: () => void;
  onLogout: () => void;
}
```

### 2.3 State Boundary Decision Tree

```
User navigates to route
  ↓
Is data route-scoped (e.g., single workflow session)?
  ├─ YES → Fetch in page.tsx, pass as props (or use Server Component)
  └─ NO → Use context provider
       ↓
  Is data global (auth, theme)?
    ├─ YES → Keep in root layout provider
    └─ NO → Feature-level provider (WorkflowProvider near /create routes)
```

### 2.4 Data-Fetching Decision Notes (Phase 2 outcome)

- Marketing/static pages (/, /about): Prefer Server Components; keep animations client-side only.
- Authenticated flows: Client components with `credentials: 'include'` via API clients (`workflowApi`, `playlistApi`).
- Route handlers vs. direct backend calls: Defer to backend FastAPI for auth/session and Spotify proxies; Next route handlers unnecessary at this stage.
- Caching: Rely on browser cache and light sessionStorage for auth; no global SWR/TanStack Query yet.
- Error handling: Normalize toast + logger usage; surface user-friendly messages.

---

## Phase 2.5: Authentication Flow Optimization Implementation

### 2.5.1 Current Auth Flow Analysis

**Problem: Current authContext.tsx behavior**
```typescript
// Issues with current implementation:
// 1. Every page mount triggers checkAuthStatus()
// 2. Network request to /auth/verify takes 200-500ms
// 3. isLoading blocks rendering during verification
// 4. On refresh, page might render before auth completes
// 5. No cookie-based optimistic state
```

**Trace of current flow:**
```
User refreshes /playlists/[id]
  ↓
1. Page component mounts
2. AuthProvider.useEffect() fires → checkAuthStatus()
3. isLoading = true (blocks UI)
4. fetch('/auth/verify') → 300ms network latency
5. Response arrives → setUser(data.user)
6. isLoading = false → page renders
   
RACE CONDITION: If page component useEffect runs before step 5,
it sees isAuthenticated=false and redirects/shows error.
```

### 2.5.2 Improved Auth Architecture

**New auth state model:**
```typescript
// lib/contexts/AuthContext.tsx (improved)
interface AuthState {
  user: User | null;
  // Split loading into stages
  isInitializing: boolean;  // First mount, checking cookies
  isValidating: boolean;    // Background verification in progress
  isValidated: boolean;     // Backend has confirmed session is valid
  error: AuthError | null;
}

type AuthStatus = 
  | 'initializing'    // Checking for session cookie
  | 'optimistic'      // Cookie found, rendering optimistically
  | 'authenticated'   // Backend verified session
  | 'unauthenticated' // No session or session invalid
  | 'error';          // Network/server error

interface AuthContextType {
  state: AuthState;
  status: AuthStatus;
  isAuthenticated: boolean;  // true for 'optimistic' | 'authenticated'
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  revalidate: () => Promise<void>;
}
```

**Improved AuthProvider implementation:**
```typescript
'use client';

import { createContext, ReactNode, useContext, useEffect, useState, useRef } from 'react';
import { getCookie } from './cookies';

const AUTH_CACHE_KEY = 'moodlist_auth_cache';
const CACHE_TTL_MS = 2 * 60 * 1000; // 2 minutes

interface CachedAuth {
  user: User;
  timestamp: number;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const verifyTimeoutRef = useRef<NodeJS.Timeout>();
  const abortControllerRef = useRef<AbortController>();

  // Check cache and cookies on mount for instant state
  useEffect(() => {
    const sessionToken = getCookie('session_token');
    
    if (!sessionToken) {
      setStatus('unauthenticated');
      return;
    }

    // Try to load from session storage cache
    const cached = getAuthCache();
    if (cached) {
      console.log('[Auth] Using cached user data');
      setUser(cached.user);
      setStatus('optimistic'); // Will revalidate in background
    } else {
      setStatus('optimistic'); // Cookie exists but no cache
    }

    // Schedule background verification (non-blocking)
    verifyTimeoutRef.current = setTimeout(() => {
      verifySession(sessionToken);
    }, 100); // Small delay to let page render first

    return () => {
      if (verifyTimeoutRef.current) {
        clearTimeout(verifyTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const getAuthCache = (): CachedAuth | null => {
    try {
      const cached = sessionStorage.getItem(AUTH_CACHE_KEY);
      if (!cached) return null;

      const data: CachedAuth = JSON.parse(cached);
      const age = Date.now() - data.timestamp;

      if (age > CACHE_TTL_MS) {
        sessionStorage.removeItem(AUTH_CACHE_KEY);
        return null;
      }

      return data;
    } catch {
      return null;
    }
  };

  const setAuthCache = (user: User) => {
    try {
      const data: CachedAuth = { user, timestamp: Date.now() };
      sessionStorage.setItem(AUTH_CACHE_KEY, JSON.stringify(data));
    } catch (err) {
      console.warn('[Auth] Failed to cache user data:', err);
    }
  };

  const clearAuthCache = () => {
    try {
      sessionStorage.removeItem(AUTH_CACHE_KEY);
    } catch {}
  };

  const verifySession = async (sessionToken: string, retryCount = 0) => {
    // Abort any in-flight verification
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${backendUrl}/api/auth/verify`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user) {
          console.log('[Auth] Session verified:', data.user.display_name);
          setUser(data.user);
          setAuthCache(data.user);
          setStatus('authenticated');
        } else {
          // Backend returned 200 but no user - session invalid
          handleInvalidSession();
        }
      } else if (response.status === 401) {
        console.log('[Auth] Session invalid (401)');
        handleInvalidSession();
      } else {
        // Server error - retry once with exponential backoff
        if (retryCount === 0) {
          await new Promise(resolve => setTimeout(resolve, 500));
          return verifySession(sessionToken, 1);
        }
        
        // After retry failure, stay optimistic but log error
        console.error('[Auth] Verification failed, staying optimistic');
        setStatus('optimistic');
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('[Auth] Verification aborted');
        return;
      }

      console.error('[Auth] Verification error:', error);
      
      // On network error, retry once
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 500));
        return verifySession(sessionToken, 1);
      }

      // Stay optimistic on persistent errors (offline, etc)
      setStatus('optimistic');
    }
  };

  const handleInvalidSession = () => {
    setUser(null);
    clearAuthCache();
    setStatus('unauthenticated');
    window.dispatchEvent(new CustomEvent('auth-expired'));
  };

  const revalidate = async () => {
    const sessionToken = getCookie('session_token');
    if (sessionToken) {
      await verifySession(sessionToken);
    }
  };

  const logout = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
      await fetch(`${backendUrl}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('[Auth] Logout error:', error);
    } finally {
      setUser(null);
      clearAuthCache();
      setStatus('unauthenticated');
      window.dispatchEvent(new Event('auth-logout'));
    }
  };

  const value: AuthContextType = {
    state: {
      user,
      isInitializing: status === 'initializing',
      isValidating: status === 'optimistic',
      isValidated: status === 'authenticated',
      error: null,
    },
    status,
    isAuthenticated: status === 'optimistic' || status === 'authenticated',
    login,
    logout,
    revalidate,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
```

### 2.5.3 Next.js Middleware for Server-Side Auth

**Create `middleware.ts` in project root:**
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = [
  '/create',
  '/playlists',
  '/playlist',
  '/profile',
];

// Routes to exclude from auth checks
const PUBLIC_ROUTES = [
  '/callback', // Spotify OAuth callback
  '/api',      // API routes handle their own auth
  '/_next',    // Next.js internals
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip auth check for public routes
  if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check if route requires authentication
  const requiresAuth = PROTECTED_ROUTES.some(route => 
    pathname.startsWith(route)
  );

  if (!requiresAuth) {
    return NextResponse.next();
  }

  // Check for session token in cookies
  const sessionToken = request.cookies.get('session_token');

  if (!sessionToken) {
    // No session cookie - redirect to home with auth required flag
    const url = request.nextUrl.clone();
    url.pathname = '/';
    url.searchParams.set('auth', 'required');
    url.searchParams.set('redirect', pathname);
    
    return NextResponse.redirect(url);
  }

  // Session cookie exists - allow through
  // (Client-side will verify validity)
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
```

### 2.5.4 AuthGuard Component for Protected Pages

**Create `components/auth/AuthGuard.tsx`:**
```typescript
'use client';

import { useAuth } from '@/lib/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { LoadingDots } from '../ui/loading-dots';

interface AuthGuardProps {
  children: React.ReactNode;
  /** If true, renders immediately with optimistic state */
  allowOptimistic?: boolean;
  /** Custom loading component */
  fallback?: React.ReactNode;
  /** Redirect destination if not authenticated */
  redirectTo?: string;
}

export function AuthGuard({ 
  children, 
  allowOptimistic = false,
  fallback,
  redirectTo = '/'
}: AuthGuardProps) {
  const { status, isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Listen for auth expiration
    const handleExpired = () => {
      const redirect = window.location.pathname;
      router.push(`${redirectTo}?auth=expired&redirect=${redirect}`);
    };

    window.addEventListener('auth-expired', handleExpired);
    return () => window.removeEventListener('auth-expired', handleExpired);
  }, [router, redirectTo]);

  // Still checking for cookies
  if (status === 'initializing') {
    return fallback || (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingDots size="sm" />
      </div>
    );
  }

  // Not authenticated
  if (status === 'unauthenticated') {
    router.push(`${redirectTo}?auth=required`);
    return null;
  }

  // Optimistic state - render immediately or wait for validation
  if (status === 'optimistic' && !allowOptimistic) {
    return fallback || (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingDots size="sm" />
      </div>
    );
  }

  // Authenticated or optimistic (when allowed)
  return <>{children}</>;
}
```

**Usage in protected pages:**
```typescript
// app/playlists/page.tsx
'use client';

import { AuthGuard } from '@/components/auth/AuthGuard';

export default function PlaylistsPage() {
  return (
    <AuthGuard allowOptimistic>
      {/* Page content renders immediately with optimistic auth */}
      <PlaylistsContent />
    </AuthGuard>
  );
}
```

### 2.5.5 Optimized Page Pattern

**Before (slow, race-prone):**
```typescript
export default function PlaylistsPage() {
  const { isAuthenticated } = useAuth(); // Blocks until verified
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
    fetchData(); // Runs after auth verified
  }, [isAuthenticated]);

  if (!isAuthenticated) return <LoadingDots />;
  return <Content data={data} />;
}
```

**After (fast, optimistic):**
```typescript
export default function PlaylistsPage() {
  return (
    <AuthGuard allowOptimistic>
      <PlaylistsContent />
    </AuthGuard>
  );
}

function PlaylistsContent() {
  const [data, setData] = useState(null);
  
  // Runs immediately, doesn't wait for auth validation
  useEffect(() => {
    fetchData(); // Backend will 401 if session invalid
  }, []);

  return <Content data={data} />;
}
```

### 2.5.6 Migration Checklist

- [ ] Update `authContext.tsx` with optimistic cookie checking
- [ ] Add session storage caching for user data
- [ ] Create `middleware.ts` for server-side route protection
- [ ] Build `<AuthGuard>` component with optimistic option
- [ ] Update all protected pages to use `<AuthGuard>`
- [ ] Remove redundant `isAuthenticated` checks from page components
- [ ] Handle `?auth=required` and `?auth=expired` query params on home page
- [ ] Test refresh behavior on all protected routes
- [ ] Verify logout clears cache and redirects properly
- [ ] Measure auth verification performance (should be <50ms for optimistic render)

---

## Phase 3: Component Refactoring Patterns

### 3.1 Navigation Decomposition Example

**Before (`Navigation.tsx`):**
```typescript
// 290 lines, mixed mobile/desktop/auth logic
export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  // ... 250+ lines of JSX
}
```

**After (split into subcomponents):**

```typescript
// layout/Navigation/Navigation.tsx
export default function Navigation({ onLogout }: NavigationProps) {
  const { user, isAuthenticated } = useAuth();

  return (
    <nav className="...">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center h-16">
          <Brand />
          <DesktopLinks items={NAV_ITEMS} />
          <div className="flex items-center gap-4">
            {isAuthenticated && user ? (
              <AuthMenu user={user} onLogout={onLogout} />
            ) : (
              <SpotifyLoginButton />
            )}
            <ThemeToggle />
            <MobileMenuTrigger />
          </div>
        </div>
        <MobileMenu items={NAV_ITEMS} />
      </div>
    </nav>
  );
}
```

```typescript
// layout/Navigation/AuthMenu.tsx
export function AuthMenu({ user, onLogout }: AuthMenuProps) {
  const { isOpen, toggle, close } = useDropdown();

  return (
    <div className="relative">
      <button onClick={toggle} className="...">
        <UserAvatar user={user} />
        <span>{user.display_name}</span>
      </button>

      {isOpen && (
        <DropdownMenu onClose={close}>
          <MenuItem href="/profile" icon={User}>Profile</MenuItem>
          <MenuItem onClick={onLogout} icon={LogOut} danger>Sign Out</MenuItem>
        </DropdownMenu>
      )}
    </div>
  );
}
```

```typescript
// layout/Navigation/hooks/useDropdown.ts
export function useDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  
  const toggle = () => setIsOpen(prev => !prev);
  const close = () => setIsOpen(false);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClick = () => close();
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, [isOpen]);

  return { isOpen, toggle, close };
}
```

### 3.2 Workflow State Simplification

**Before (`workflowContext.tsx`):**
```typescript
// 607 lines, managing:
// - Start/load/stop/reset workflow
// - Polling logic
// - Playlist edits
// - Spotify sync
// - Track search
```

**After (responsibilities split):**

```typescript
// contexts/WorkflowContext.tsx - Core state only
export function WorkflowProvider({ children }: Props) {
  const [state, setState] = useState<WorkflowState>(initialState);
  
  const api = useWorkflowApi(); // Extracted API calls
  const { startPolling, stopPolling } = useWorkflowPolling(state.sessionId); // Extracted polling

  return (
    <WorkflowContext.Provider value={{ state, api, polling: { start: startPolling, stop: stopPolling } }}>
      {children}
    </WorkflowContext.Provider>
  );
}
```

```typescript
// hooks/useWorkflowApi.ts - API layer
export function useWorkflowApi() {
  const startWorkflow = async (mood: string, genre?: string) => {
    // API call logic
  };

  const loadWorkflow = async (sessionId: string) => {
    // API call logic
  };

  return { startWorkflow, loadWorkflow, /* ... */ };
}
```

```typescript
// hooks/useWorkflowPolling.ts - Polling abstraction
export function useWorkflowPolling(sessionId: string | null) {
  useEffect(() => {
    if (!sessionId) return;

    const interval = setInterval(async () => {
      // Poll for updates
    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  return { startPolling, stopPolling };
}
```

### 3.3 Playlist Editor Decomposition

**Before:**
```typescript
// PlaylistEditor.tsx - 624 lines
// Contains: DnD setup, track list, search UI, Spotify sync, save logic
```

**After:**

```typescript
// features/playlist/PlaylistEditor/PlaylistEditor.tsx - Main orchestrator
export function PlaylistEditor({ sessionId, recommendations, onSave }: Props) {
  const { tracks, reorder, remove, add } = usePlaylistEdits(sessionId, recommendations);
  const [isSearchOpen, setSearchOpen] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Your Playlist</CardTitle>
        <Button onClick={() => setSearchOpen(true)}>
          <Plus /> Add Track
        </Button>
      </CardHeader>
      <CardContent>
        <TrackList 
          tracks={tracks} 
          onReorder={reorder}
          onRemove={remove}
        />
      </CardContent>
      <CardFooter>
        <SaveButtons onSave={onSave} />
      </CardFooter>

      <TrackSearchDialog
        open={isSearchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={add}
      />
    </Card>
  );
}
```

```typescript
// features/playlist/PlaylistEditor/TrackList.tsx
export function TrackList({ tracks, onReorder, onRemove }: TrackListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = tracks.findIndex(t => t.track_id === active.id);
      const newIndex = tracks.findIndex(t => t.track_id === over.id);
      onReorder(oldIndex, newIndex);
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={tracks.map(t => t.track_id)} strategy={verticalListSortingStrategy}>
        {tracks.map((track, idx) => (
          <TrackItem key={track.track_id} track={track} index={idx} onRemove={onRemove} />
        ))}
      </SortableContext>
    </DndContext>
  );
}
```

```typescript
// features/playlist/PlaylistEditor/usePlaylistEdits.ts
export function usePlaylistEdits(sessionId: string, initialTracks: Track[]) {
  const [tracks, setTracks] = useState(initialTracks);
  const { applyCompletedEdit } = useWorkflow();

  const reorder = async (oldIndex: number, newIndex: number) => {
    // Optimistic update
    setTracks(arrayMove(tracks, oldIndex, newIndex));

    try {
      await applyCompletedEdit('reorder', { trackId: tracks[oldIndex].track_id, newPosition: newIndex });
    } catch (err) {
      // Rollback
      setTracks(initialTracks);
      toast.error('Failed to reorder track');
    }
  };

  const remove = async (trackId: string) => {
    const original = tracks;
    setTracks(tracks.filter(t => t.track_id !== trackId));

    try {
      await applyCompletedEdit('remove', { trackId });
    } catch (err) {
      setTracks(original);
      toast.error('Failed to remove track');
    }
  };

  const add = async (trackUri: string) => {
    // Implementation
  };

  return { tracks, reorder, remove, add };
}
```

---

## Phase 4: Redundancy Elimination Patterns

### 4.1 Consolidated Toast Usage

**Before (scattered across files):**
```typescript
// In MoodInput.tsx
toast.error('Please enter a mood');

// In PlaylistEditor.tsx
toast.success('Track removed successfully');

// In workflowContext.tsx
toast('Workflow started', { duration: 2000 });
```

**After (centralized helper):**
```typescript
// lib/hooks/useToast.ts
export const useToast = () => {
  return {
    success: (message: string) => toast.success(message, { duration: 3000 }),
    error: (message: string) => toast.error(message, { duration: 5000 }),
    info: (message: string) => toast.info(message),
    promise: <T,>(
      promise: Promise<T>,
      messages: { loading: string; success: string; error: string }
    ) => toast.promise(promise, messages),
  };
};

// Usage
const { success, error, promise } = useToast();
await promise(
  applyEdit(),
  { 
    loading: 'Updating playlist...', 
    success: 'Playlist updated!', 
    error: 'Update failed' 
  }
);
```

### 4.2 Marketing Section Parameterization

**Before (duplication in / and /about):**
```typescript
// page.tsx
<section>
  <h2>Create Mood-Based Playlists</h2>
  <p>Our AI analyzes your mood...</p>
</section>

// about/page.tsx
<section>
  <h2>Create Mood-Based Playlists</h2>
  <p>Our AI analyzes your mood...</p>
</section>
```

**After (reusable component):**
```typescript
// marketing/FeatureHighlight.tsx
export function FeatureHighlight({ 
  title, 
  description, 
  icon: Icon, 
  variant = 'default' 
}: FeatureHighlightProps) {
  return (
    <section className={cn('py-16', variant === 'hero' && 'py-24')}>
      <Icon className="w-12 h-12 mb-4" />
      <h2 className="text-3xl font-bold">{title}</h2>
      <p className="text-muted-foreground">{description}</p>
    </section>
  );
}

// Usage
<FeatureHighlight
  title="Create Mood-Based Playlists"
  description="Our AI analyzes your mood..."
  icon={Sparkles}
  variant="hero"
/>
```

### 4.3 Auth Guard Pattern

**Before (repeated checks):**
```typescript
// In multiple pages
const handleAction = () => {
  if (!isAuthenticated) {
    setShowLoginDialog(true);
    return;
  }
  // ... action logic
};
```

**After (reusable hook):**
```typescript
// hooks/useAuthGuard.ts
export function useAuthGuard() {
  const { isAuthenticated } = useAuth();
  const [showDialog, setShowDialog] = useState(false);

  const requireAuth = <T extends any[]>(
    callback: (...args: T) => void | Promise<void>
  ) => {
    return (...args: T) => {
      if (!isAuthenticated) {
        setShowDialog(true);
        return;
      }
      return callback(...args);
    };
  };

  return { 
    requireAuth, 
    LoginDialog: () => <LoginRequiredDialog open={showDialog} onOpenChange={setShowDialog} /> 
  };
}

// Usage
function MyComponent() {
  const { requireAuth, LoginDialog } = useAuthGuard();

  const handleSubmit = requireAuth(async (mood: string) => {
    await startWorkflow(mood);
  });

  return (
    <>
      <button onClick={() => handleSubmit('happy')}>Create</button>
      <LoginDialog />
    </>
  );
}
```

### 4.4 Logging & Refresh Hygiene

**Problem:** Debug `console.log` statements and full-page reloads scattered throughout codebase.

**Impact:**
- Noisy browser console in production
- Lost state on page refresh
- Poor debugging traceability
- Negative UX with flash of white screen

#### Structured Logger Implementation

```typescript
// lib/utils/logger.ts
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  component?: string;
  action?: string;
  [key: string]: unknown;
}

class Logger {
  private isDev = process.env.NODE_ENV === 'development';

  private log(level: LogLevel, message: string, context?: LogContext) {
    if (!this.isDev && level === 'debug') return;

    const timestamp = new Date().toISOString();
    const contextStr = context ? ` ${JSON.stringify(context)}` : '';
    const entry = `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;

    switch (level) {
      case 'error':
        console.error(entry);
        // Integrate with Sentry or error tracking here
        break;
      case 'warn':
        console.warn(entry);
        break;
      default:
        console.log(entry);
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
      errorMessage: error?.message,
      stack: error?.stack,
    });
  }
}

export const logger = new Logger();
```

**Migration examples:**
```typescript
// Before
console.log('Polling already active for session:', sessionId);

// After
logger.debug('Polling already active', { 
  component: 'PollingManager', 
  sessionId 
});

// Before
console.error('Auth check failed:', error);

// After
logger.error('Auth check failed', error, { component: 'AuthContext' });
```

#### Replace window.location.reload()

**Affected files:**
- Navigation.tsx (2x)
- create/page.tsx (2x)
- create/[id]/page.tsx (3x)
- playlists/page.tsx (1x)

```typescript
// Before
const handleLogout = async () => {
  await logout();
  window.location.href = '/';
};

// After
import { useRouter } from 'next/navigation';

const router = useRouter();
const handleLogout = async () => {
  await logout();
  router.push('/');
  router.refresh(); // Revalidate server state
};

// Before
const handleEditComplete = () => {
  window.location.reload();
};

// After
const handleEditComplete = async () => {
  await refreshResults(); // Refresh context state
  router.push(`/playlist/${sessionId}`);
};
```

**Checklist:**
- [ ] Create `lib/utils/logger.ts`
- [ ] Replace all `console.log` → `logger.debug`
- [ ] Replace all `console.error` → `logger.error`
- [ ] Add ESLint rule: `no-console` with auto-fix
- [ ] Remove all `window.location.reload()` calls
- [ ] Replace with router.refresh() or state updates
- [ ] Test all affected flows

---

## Phase 5: Performance Optimization Strategies

### 5.1 Code Splitting Strategy

```typescript
// app/create/page.tsx - Lazy load heavy editor
import dynamic from 'next/dynamic';

const PlaylistEditor = dynamic(
  () => import('@/components/features/playlist/PlaylistEditor'),
  { 
    loading: () => <EditorSkeleton />,
    ssr: false // DnD requires client-side only
  }
);
```

### 5.2 Memoization Best Practices

```typescript
// Before
function TrackList({ tracks, onRemove }) {
  return tracks.map(track => (
    <TrackItem 
      track={track} 
      onRemove={onRemove} // Creates new function every render
    />
  ));
}

// After
const TrackItem = memo(function TrackItem({ track, onRemove }) {
  return (/* ... */);
});

function TrackList({ tracks, onRemove }) {
  const handleRemove = useCallback((trackId: string) => {
    onRemove(trackId);
  }, [onRemove]);

  return tracks.map(track => (
    <TrackItem 
      key={track.track_id}
      track={track} 
      onRemove={handleRemove}
    />
  ));
}
```

### 5.3 Virtual Scrolling for Large Lists

```typescript
// For playlists with 50+ tracks
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualTrackList({ tracks }: { tracks: Track[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: tracks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80, // Track row height
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <TrackItem track={tracks[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 5.4 Server Component Migration

```typescript
// Before (Client Component)
'use client';
export default function PlaylistsPage() {
  const [playlists, setPlaylists] = useState([]);
  useEffect(() => {
    fetch('/api/playlists').then(/* ... */);
  }, []);
  return <PlaylistGrid playlists={playlists} />;
}

// After (Server Component)
import { playlistAPI } from '@/lib/api/playlist';

export default async function PlaylistsPage() {
  const playlists = await playlistAPI.getUserPlaylists();
  return <PlaylistGrid playlists={playlists} />;
}
```

---

## Phase 6: Testing & Quality Assurance

### 6.1 Component Test Template

```typescript
// __tests__/components/MoodInput.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MoodInput } from '@/components/features/mood/MoodInput';

describe('MoodInput', () => {
  it('validates empty input', async () => {
    const onSubmit = jest.fn();
    render(<MoodInput onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/please enter a mood/i)).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits valid mood', async () => {
    const onSubmit = jest.fn();
    render(<MoodInput onSubmit={onSubmit} />);

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'happy' } });
    fireEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith('happy', undefined);
    });
  });
});
```

### 6.2 Integration Test Example

```typescript
// __tests__/flows/create-playlist.test.tsx
import { test, expect } from '@playwright/test';

test('create playlist flow', async ({ page }) => {
  // Mock auth
  await page.goto('/create');
  await page.getByRole('textbox').fill('energetic');
  await page.getByRole('button', { name: /create/i }).click();

  // Wait for workflow
  await expect(page.getByText(/analyzing your mood/i)).toBeVisible();
  await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 30000 });

  // Verify results
  const tracks = page.locator('[data-testid="track-item"]');
  await expect(tracks).toHaveCount(20);
});
```

### 6.3 Type Safety Improvements

```typescript
// Before (loose types)
interface WorkflowState {
  status: string | null;
  error: string | null;
}

// After (discriminated union)
type WorkflowState = 
  | { status: 'idle'; sessionId: null; error: null; }
  | { status: 'loading'; sessionId: null; error: null; }
  | { status: 'running'; sessionId: string; error: null; currentStep: string; }
  | { status: 'completed'; sessionId: string; error: null; recommendations: Track[]; }
  | { status: 'failed'; sessionId: string; error: string; };

// Type-safe state access
if (state.status === 'completed') {
  // TypeScript knows recommendations exists here
  console.log(state.recommendations);
}
```

---

## Rollout Strategy

### Feature Flag Implementation

```typescript
// lib/feature-flags.ts
export const FLAGS = {
  NEW_NAVIGATION: process.env.NEXT_PUBLIC_FF_NEW_NAV === 'true',
  VIRTUAL_SCROLLING: process.env.NEXT_PUBLIC_FF_VIRTUAL_SCROLL === 'true',
} as const;

// Usage
import { FLAGS } from '@/lib/feature-flags';

export default function MyPage() {
  return FLAGS.NEW_NAVIGATION ? <NewNavigation /> : <Navigation />;
}
```

### Monitoring Setup

```typescript
// lib/monitoring.ts
export function trackRefactorMetric(component: string, metric: string, value: number) {
  if (typeof window === 'undefined') return;
  
  // Send to analytics
  window.gtag?.('event', 'refactor_metric', {
    component,
    metric,
    value,
  });
}

// Usage
useEffect(() => {
  const start = performance.now();
  return () => {
    trackRefactorMetric('PlaylistEditor', 'mount_time', performance.now() - start);
  };
}, []);
```

---

## Success Metrics

Track these KPIs throughout the refactor:

| Metric | Baseline | Target | Phase |
|--------|----------|--------|-------|
| Total bundle size | TBD | -20% | 5 |
| Largest component LOC | 624 | <300 | 3 |
| Test coverage | ~0% | >70% | 6 |
| Lighthouse Performance | TBD | >90 | 5 |
| Context re-renders (DevTools) | TBD | -50% | 3 |
| TypeScript strict errors | TBD | 0 | 6 |

---

This implementation guide provides concrete patterns and examples that development teams can reference when executing each phase of the refactor plan.
