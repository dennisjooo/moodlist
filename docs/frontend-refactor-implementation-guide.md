# Frontend Refactor Implementation Guide

Companion to the main refactoring plan, this guide provides technical implementation details, example patterns, and code snippets for each phase.

---

## Phase 1: Implementation Details

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

### 2.1 Component Folder Structure (Proposed)

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
