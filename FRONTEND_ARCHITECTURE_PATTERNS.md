# Frontend Architecture Patterns & Best Practices

## Overview
This document outlines the established patterns in the MoodList frontend and provides guidelines for maintaining consistency. It serves as a reference for understanding the codebase architecture and making future development decisions.

---

## 1. Project Structure

### Directory Organization
```
frontend/src/
├── app/                      # Next.js 15 App Router pages
│   ├── (route)/page.tsx     # Route pages
│   ├── layout.tsx           # Root layout with providers
│   └── globals.css          # Global styles
├── components/              # React components
│   ├── features/            # Feature-specific components
│   │   ├── auth/           # Authentication UI
│   │   ├── create/         # Playlist creation
│   │   ├── marketing/      # Landing page sections
│   │   ├── playlist/       # Playlist management
│   │   ├── profile/        # User profile
│   │   └── workflow/       # Workflow status
│   ├── layout/             # Layout components (nav, footer)
│   ├── shared/             # Shared components (loading states)
│   └── ui/                 # Reusable UI primitives (shadcn/ui)
├── lib/                    # Core application logic
│   ├── api/               # API service layers
│   ├── contexts/          # React contexts (Auth, Workflow)
│   ├── hooks/             # Custom React hooks
│   │   ├── accessibility/ # A11y hooks
│   │   ├── auth/          # Auth-related hooks
│   │   ├── navigation/    # Navigation helpers
│   │   ├── playlist/      # Playlist operations
│   │   ├── profile/       # Profile data
│   │   ├── ui/            # UI utilities
│   │   └── workflow/      # Workflow management
│   ├── types/             # TypeScript type definitions
│   ├── utils/             # Utility functions
│   ├── config.ts          # App configuration
│   └── constants.ts       # App constants
└── proxy.ts               # Development proxy config
```

### Key Principles
- **Feature-based organization**: Components grouped by feature domain
- **Clear separation**: UI components vs business logic hooks
- **Consistent exports**: Index files for clean imports
- **Colocation**: Related files grouped together

---

## 2. State Management Patterns

### Context Providers

The app uses React Context for global state with two main providers:

#### AuthContext
```typescript
// Purpose: Manage user authentication state
// Location: src/lib/contexts/AuthContext.tsx
// Provides:
- user: User | null
- isLoading: boolean
- isAuthenticated: boolean
- isValidated: boolean
- login: (accessToken, refreshToken) => Promise<void>
- logout: () => Promise<void>
- refreshUser: () => Promise<void>
```

**Key Features:**
- Optimistic authentication with cache
- Background verification
- Session cookie management
- Auth event broadcasting (auth-update, auth-logout, auth-expired)

#### WorkflowContext
```typescript
// Purpose: Manage playlist creation workflow state
// Location: src/lib/contexts/WorkflowContext.tsx
// Provides:
- workflowState: WorkflowState
- startWorkflow: (moodPrompt) => Promise<void>
- loadWorkflow: (sessionId) => Promise<void>
- stopWorkflow: () => void
- resetWorkflow: () => void
- applyCompletedEdit: (editType, options) => Promise<void>
- searchTracks: (query) => Promise<SearchResult>
- refreshResults: () => Promise<void>
- saveToSpotify: () => Promise<SaveResult>
- syncFromSpotify: () => Promise<SyncResult>
- clearError: () => void
```

**Key Features:**
- SSE streaming with polling fallback
- Monotonic status progression (prevents backwards updates)
- Optimistic UI updates
- Path-based streaming (only on /create/[id])
- Event-based notifications

### Provider Composition

```typescript
// src/app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>           {/* Auth state first */}
          <WorkflowProvider>     {/* Workflow depends on auth */}
            <ThemeProvider>      {/* UI preferences */}
              {children}
            </ThemeProvider>
          </WorkflowProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
```

**Ordering Rationale:**
1. AuthProvider first - required by workflow operations
2. WorkflowProvider second - uses auth context
3. ThemeProvider last - pure UI concern

---

## 3. Custom Hooks Pattern

### Hook Organization

Custom hooks are organized by domain:

```typescript
// src/lib/hooks/index.ts - Central export point
export * from './accessibility';
export * from './auth';
export * from './navigation';
export * from './playlist';
export * from './profile';
export * from './ui';
export * from './workflow';
```

### Hook Naming Convention

- `use[Feature][Action]` - e.g., `useWorkflowActions`, `usePlaylistEdits`
- `use[Feature]State` - e.g., `useWorkflowState` (state management)
- `use[Feature]` - e.g., `useProfile` (data fetching)

### Common Hook Patterns

#### State Management Hook
```typescript
// Pattern: Encapsulate complex state logic
export function useWorkflowState() {
  const [state, setState] = useState(initialState);
  
  const updateState = useCallback((data) => {
    setState(prev => ({ ...prev, ...data }));
  }, []);
  
  return {
    state,
    updateState,
    // ... other state operations
  };
}
```

#### Action Hook
```typescript
// Pattern: Encapsulate business logic operations
export function useWorkflowActions({ workflowState, setLoading, setWorkflowData }) {
  const startWorkflow = useCallback(async (moodPrompt: string) => {
    setLoading(true);
    try {
      const response = await workflowAPI.startWorkflow({ mood_prompt: moodPrompt });
      setWorkflowData({
        sessionId: response.session_id,
        status: 'pending',
        moodPrompt,
      });
    } catch (error) {
      // Error handling
    } finally {
      setLoading(false);
    }
  }, [setLoading, setWorkflowData]);
  
  return {
    startWorkflow,
    // ... other actions
  };
}
```

#### Data Fetching Hook
```typescript
// Pattern: Fetch and cache data
export function useProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    loadProfile();
  }, []);
  
  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const data = await profileAPI.getProfile();
      setProfile(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  return {
    profile,
    isLoading,
    error,
    refreshProfile: loadProfile,
  };
}
```

---

## 4. API Service Layer Pattern

### Service Class Structure

```typescript
// Pattern: Singleton service class
class WorkflowAPI {
  // Private request wrapper
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${config.api.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include',
      ...options,
    });
    
    if (!response.ok) {
      const errorMessage = await extractErrorMessage(response);
      throw new WorkflowAPIError(response.status, errorMessage);
    }
    
    return response.json();
  }
  
  // Public API methods
  async startWorkflow(request: StartWorkflowRequest): Promise<StartWorkflowResponse> {
    return this.request('/api/agents/recommendations/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }
  
  // ... other methods
}

// Export singleton instance
export const workflowAPI = new WorkflowAPI();
```

### API Error Handling

```typescript
class WorkflowAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'WorkflowAPIError';
  }
}

// Usage in hooks
try {
  await workflowAPI.startWorkflow(request);
} catch (error) {
  if (error instanceof WorkflowAPIError) {
    // Handle API error with status code
    if (error.status === 429) {
      showError('Rate limit exceeded');
    }
  } else {
    // Handle network error
    showError('Network error');
  }
}
```

---

## 5. Component Patterns

### Page Components (App Router)

```typescript
// Pattern: Server Component (default)
export default async function PlaylistsPage() {
  // Can access cookies, headers server-side
  const cookieStore = await cookies();
  const isLoggedIn = Boolean(cookieStore.get('session_token'));
  
  return (
    <div>
      <Navigation />
      <PlaylistsPageContent initialAuth={isLoggedIn} />
    </div>
  );
}

// Pattern: Client Component with Auth Guard
'use client';

export default function CreatePage() {
  return (
    <AuthGuard optimistic={true}>
      <CreatePageContent />
    </AuthGuard>
  );
}
```

### Feature Components

```typescript
// Pattern: Feature component with hooks
'use client';

export function PlaylistEditor({ sessionId, recommendations }: PlaylistEditorProps) {
  const {
    tracks,
    reorderTrack,
    removeTrack,
    addTrack,
    // ... all playlist operations
  } = usePlaylistEdits({ sessionId, initialTracks: recommendations });
  
  return (
    <div>
      <TrackList 
        tracks={tracks}
        onReorder={reorderTrack}
        onRemove={removeTrack}
      />
      <TrackSearch onAdd={addTrack} />
    </div>
  );
}
```

### UI Primitive Components (shadcn/ui)

```typescript
// Pattern: Forwarded ref, variant-based styling
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground',
        outline: 'border border-input bg-background',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
```

---

## 6. Real-time Updates Pattern

### SSE with Polling Fallback

```typescript
// Pattern: Progressive enhancement
export function useWorkflowSSE(
  sessionId: string | null,
  status: WorkflowStatus['status'] | null,
  options: {
    enabled: boolean;
    callbacks: {
      onStatus: (status: WorkflowStatus) => void;
      onTerminal: (status: WorkflowStatus, results: WorkflowResults | null) => void;
      onError: (error: Error) => void;
      onAwaitingInput: () => void;
    };
  }
) {
  const [useSSE, setUseSSE] = useState(true);
  
  // Attempt SSE first
  useEffect(() => {
    if (!options.enabled || !sessionId) return;
    
    if (useSSE) {
      try {
        const eventSource = new EventSource(
          workflowAPI.getStreamUrl(sessionId),
          { withCredentials: true }
        );
        
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data);
          options.callbacks.onStatus(data);
        };
        
        eventSource.onerror = () => {
          setUseSSE(false); // Fall back to polling
        };
        
        return () => eventSource.close();
      } catch {
        setUseSSE(false); // Browser doesn't support SSE
      }
    }
  }, [sessionId, options.enabled, useSSE]);
  
  // Fallback polling
  useWorkflowPolling(sessionId, status, {
    enabled: options.enabled && !useSSE,
    callbacks: options.callbacks,
  });
}
```

### Polling Strategy

```typescript
// Pattern: Adaptive polling based on status
export function useWorkflowPolling(
  sessionId: string | null,
  status: WorkflowStatus['status'] | null,
  options: PollingOptions
) {
  useEffect(() => {
    if (!options.enabled || !sessionId) return;
    
    // Calculate polling interval based on status
    const interval = status === 'awaiting_input' 
      ? config.polling.awaitingInputInterval
      : status === 'pending'
      ? config.polling.pendingInterval
      : config.polling.baseInterval;
    
    const poll = async () => {
      try {
        const data = await workflowAPI.getWorkflowStatus(sessionId);
        options.callbacks.onStatus(data);
      } catch (error) {
        options.callbacks.onError(error);
      }
    };
    
    const timer = setInterval(poll, interval);
    return () => clearInterval(timer);
  }, [sessionId, status, options]);
}
```

---

## 7. Optimistic Updates Pattern

### Playlist Editing

```typescript
// Pattern: Update UI immediately, revert on error
const removeTrack = useCallback(async (trackId: string) => {
  // Store original state for rollback
  const originalTracks = tracks;
  
  // Mark as removing (show loading indicator)
  setRemovingTracks(prev => new Set(prev).add(trackId));
  
  try {
    // Optimistic update
    setTracks(prev => prev.filter(track => track.track_id !== trackId));
    
    // Apply to server
    await applyCompletedEdit('remove', { trackId });
  } catch (error) {
    // Revert on error
    setTracks(originalTracks);
    showError('Failed to remove track');
  } finally {
    // Clear loading indicator
    setRemovingTracks(prev => {
      const newSet = new Set(prev);
      newSet.delete(trackId);
      return newSet;
    });
  }
}, [tracks, applyCompletedEdit, showError]);
```

---

## 8. Error Handling Pattern

### Standardized Error Flow

```typescript
// 1. Define error boundaries at route level
export function CreateSessionPage() {
  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <AuthGuard>
        <CreateSessionPageContent />
      </AuthGuard>
    </ErrorBoundary>
  );
}

// 2. Handle errors in hooks
export function useWorkflowActions() {
  const { error: showError } = useToast();
  
  const startWorkflow = useCallback(async (moodPrompt: string) => {
    try {
      await workflowAPI.startWorkflow({ mood_prompt: moodPrompt });
    } catch (error) {
      // Parse and log error
      const appError = handleError(error, {
        component: 'useWorkflowActions',
        action: 'startWorkflow',
      });
      
      // Show user-friendly message
      showError(appError.message);
    }
  }, [showError]);
  
  return { startWorkflow };
}

// 3. Display errors in components
export function CreateSessionError({ error, onBack }: ErrorProps) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <p>{error || 'Failed to create playlist'}</p>
      <Button onClick={onBack}>Go Back</Button>
    </div>
  );
}
```

---

## 9. Loading States Pattern

### Progressive Loading

```typescript
// Pattern: Skeleton → Loading → Content
export function CreateSessionPage() {
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const { workflowState } = useWorkflow();
  
  // Show minimal skeleton during initial load
  if (isLoadingSession) {
    return <CreateSessionSkeleton />;
  }
  
  // Show progress during workflow execution
  if (workflowState.status && !isTerminalStatus(workflowState.status)) {
    return (
      <CreateSessionProgress 
        status={workflowState.status}
        currentStep={workflowState.currentStep}
      />
    );
  }
  
  // Show final content
  return <CreateSessionResults />;
}
```

### Suspense for Code Splitting

```typescript
// Pattern: Lazy load below-the-fold content
const FeaturesSection = dynamic(() => import('@/components/FeaturesSection'), {
  loading: () => <div className="h-[400px]" />, // Preserve layout
});

export default function Home() {
  return (
    <div>
      <HeroSection />
      <FeaturesSection />
    </div>
  );
}
```

---

## 10. Type Safety Patterns

### Strict Type Definitions

```typescript
// Pattern: Export types from API layer
export interface WorkflowStatus {
  session_id: string;
  status: "pending" | "analyzing_mood" | "completed" | "failed";
  current_step: string;
  mood_analysis?: MoodAnalysis;
  // ... other fields
}

// Pattern: Derive types from API responses
export type Track = WorkflowResults['recommendations'][number];

// Pattern: Props interfaces for components
export interface PlaylistEditorProps {
  sessionId: string;
  recommendations: Track[];
  isCompleted?: boolean;
  onSave?: () => void;
  onCancel?: () => void;
}
```

### Type Guards

```typescript
// Pattern: Runtime type checking
function isWorkflowAPIError(error: unknown): error is WorkflowAPIError {
  return error instanceof WorkflowAPIError;
}

// Usage
try {
  await workflowAPI.startWorkflow(request);
} catch (error) {
  if (isWorkflowAPIError(error)) {
    handleAPIError(error);
  } else {
    handleUnknownError(error);
  }
}
```

---

## 11. Performance Optimization Patterns

### Memoization

```typescript
// Pattern: Memoize expensive computations
const deduplicatedTracks = useMemo(() =>
  initialTracks.filter((track, index, arr) =>
    arr.findIndex(t => t.track_id === track.track_id) === index
  ), [initialTracks]
);

// Pattern: Memoize callbacks passed to children
const handleReorder = useCallback((oldIndex: number, newIndex: number) => {
  // ... reorder logic
}, [tracks, applyCompletedEdit]);
```

### Debouncing

```typescript
// Pattern: Debounce user input
const [searchQuery, setSearchQuery, debouncedQuery] = useDebouncedSearch('', undefined, 300);

useEffect(() => {
  if (!debouncedQuery) return;
  
  searchTracks(debouncedQuery);
}, [debouncedQuery, searchTracks]);
```

### Code Splitting

```typescript
// Pattern: Dynamic imports for large features
const PlaylistEditor = dynamic(
  () => import('@/components/features/playlist/PlaylistEditor'),
  { 
    loading: () => <EditorSkeleton />,
    ssr: false // Client-only component
  }
);
```

---

## 12. Accessibility Patterns

### Keyboard Navigation

```typescript
// Pattern: Custom keyboard shortcuts
export function useKeyboardShortcuts(shortcuts: Record<string, () => void>) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const key = `${event.ctrlKey ? 'Ctrl+' : ''}${event.key}`;
      const handler = shortcuts[key];
      if (handler) {
        event.preventDefault();
        handler();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// Usage
useKeyboardShortcuts({
  'Escape': () => setShowDialog(false),
  'Ctrl+s': () => handleSave(),
});
```

### ARIA Attributes

```typescript
// Pattern: Proper ARIA labels
<button
  aria-label="Remove track from playlist"
  aria-busy={isRemoving}
  disabled={isRemoving}
  onClick={() => removeTrack(trackId)}
>
  {isRemoving ? <Spinner /> : <X />}
</button>
```

---

## 13. Testing Patterns

### Hook Testing

```typescript
// Pattern: Test hooks with renderHook
import { renderHook, act } from '@testing-library/react';
import { useWorkflowState } from './useWorkflowState';

describe('useWorkflowState', () => {
  it('should update workflow status', () => {
    const { result } = renderHook(() => useWorkflowState());
    
    act(() => {
      result.current.handleStatusUpdate({
        session_id: '123',
        status: 'pending',
        current_step: 'Starting...',
      });
    });
    
    expect(result.current.workflowState.status).toBe('pending');
  });
});
```

### Component Testing

```typescript
// Pattern: Test components with user interactions
import { render, screen, fireEvent } from '@testing-library/react';
import { PlaylistEditor } from './PlaylistEditor';

describe('PlaylistEditor', () => {
  it('should remove track when clicking remove button', async () => {
    const onRemove = jest.fn();
    render(
      <PlaylistEditor 
        tracks={mockTracks}
        onRemove={onRemove}
      />
    );
    
    const removeButton = screen.getByLabelText('Remove track');
    fireEvent.click(removeButton);
    
    expect(onRemove).toHaveBeenCalledWith('track-id-1');
  });
});
```

---

## Best Practices Summary

### Do's ✅
- Use TypeScript strict mode
- Extract complex logic into custom hooks
- Implement optimistic updates for better UX
- Use proper ARIA attributes for accessibility
- Log errors with context for debugging
- Memoize expensive computations and callbacks
- Use debouncing for search and user input
- Implement progressive loading (skeleton → content)
- Handle errors gracefully with fallbacks
- Write tests for critical workflows

### Don'ts ❌
- Don't mix business logic in components
- Don't use inline styles (use Tailwind classes)
- Don't ignore TypeScript errors
- Don't forget error boundaries
- Don't skip loading states
- Don't make API calls in components directly
- Don't forget to cleanup effects (timers, listeners)
- Don't use `any` type without justification
- Don't create circular dependencies
- Don't bypass authentication guards

---

## Conclusion

These patterns and practices form the foundation of the MoodList frontend architecture. Following these guidelines ensures:

- **Consistency**: Code looks and behaves uniformly
- **Maintainability**: Easy to understand and modify
- **Scalability**: Architecture supports growth
- **Quality**: High standards for user experience
- **Performance**: Optimized for speed and efficiency

When in doubt, refer to existing implementations in the codebase that follow these patterns.
