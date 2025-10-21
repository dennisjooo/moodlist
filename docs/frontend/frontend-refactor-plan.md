# Frontend Refactor Plan

This plan outlines a phased approach for refactoring the MoodList frontend (Next.js 15, React 19, Tailwind CSS 4) to improve maintainability, performance, and scalability. Each phase builds on the previous one and should produce tangible deliverables before moving forward.

---

## Guiding Principles

- **Incremental delivery:** Keep the app deployable after every phase; prefer feature-flagged releases over long-lived refactor branches.
- **Preserve user experience:** Match current behavior and visual design unless a UX improvement is explicitly scoped.
- **Measure and validate:** Capture performance and bundle metrics before/after changes to prove improvements.
- **Lean on existing abstractions:** Prefer enhancing current context/providers (e.g., `authContext`, `workflowContext`) before introducing brand new state libraries.

---

## Phase 1 – Initial Assessment & Discovery (COMPLETED ✅)

### Objectives

- ✅ Establish baseline knowledge of component complexity, routing, data dependencies, and performance bottlenecks.
- ✅ Document current architectural pain points (e.g., 600+ line monolithic components, duplicated UI patterns).
- ✅ **BONUS**: Implemented critical auth performance optimizations (originally planned as Phase 2.5).

### Detailed Steps

1. **✅ Inventory the application structure**: Mapped `src/app/*` routes, shared UI libraries from `src/components/ui`, and context providers under `src/lib`.
2. **✅ Complexity audit**: Identified oversized files (`Navigation.tsx` 290 lines, `PlaylistEditor.tsx` 624 lines, `workflowContext.tsx` 607 lines) and flagged candidates for decomposition.
3. **✅ State-flow tracing**: Documented authentication, workflow, and playlist state flows between pages.
4. **✅ Performance profiling**: Established baseline metrics (auth check: 300ms, bundle size: TBD, largest component: 624 LOC).
5. **✅ DX evaluation**: Reviewed ESLint/Prettier/TypeScript configs and established shared utilities.
6. **✅ BONUS: Auth optimization**: Implemented optimistic rendering, middleware protection, and SessionStorage caching (83% performance improvement).

### Implementation Results

**Auth Performance Improvement:**

- **Before**: 300ms auth verification (2-3 database queries)
- **After**: <50ms auth verification (1 optimized database query + frontend caching)
- **Improvement**: 83% faster auth checks

**Key Deliverables:**

- Complete application architecture inventory
- Component complexity analysis with line counts
- Performance baseline metrics established
- Auth flow optimizations implemented ahead of schedule
- Centralized configuration and logging infrastructure

**Unexpected Benefits:**

- Critical UX issue (auth flashing) resolved during assessment phase
- Frontend/backend collaboration opportunity identified and executed
- Performance baseline captured before optimization

### Best Practices

- Record findings in a shared document and link line numbers/metrics for traceability.
- Prioritize issues by impact and effort to feed the backlog for later phases.

---

## Phase 2 – Architecture & Component Strategy

### Objectives

- Define the target component hierarchy, routing conventions, and state ownership boundaries.
- Decide on reusable primitives (layout scaffolding, typography, form controls) and where they live.

### Detailed Steps

1. **Module boundary definition**: Group pages into user journeys (Marketing, Create Flow, Playlist Management, Account) and outline shared building blocks.
2. **Component taxonomy**: Create a design token & component inventory, tagging items for refactor, reuse, or removal.
3. **State ownership plan**: Determine what remains in client contexts (e.g., workflow state) versus new server components or React cache, considering Next.js 15 capabilities.
4. **Data-fetching strategy**: Document when to use server actions, route handlers, or client fetches—especially for playlist CRUD and Spotify proxy calls.
5. **Dependency evaluation**: Decide whether to introduce helpers (e.g., TanStack Query) or extend current utilities (`workflowApi`, `playlistApi`).
6. **Authentication lifecycle design**: Audit `/api/auth/verify` usage, model a faster verification flow (e.g., SSR session checks + client revalidation), and define how protected routes block rendering until auth state is known.

### Potential Challenges

- Balancing server vs. client component boundaries without rewriting business logic.
- Avoiding over-abstraction that slows down delivery.

### Best Practices

- Produce architecture diagrams (component tree + data flow) and circulate for review.
- Favor composition over inheritance; design APIs that are prop-driven and tree-shakeable.

---

## Phase 2.5 – Authentication Flow Optimization (COMPLETED ✅ as part of Phase 1)

**Note:** Originally planned as a separate phase but implemented during Phase 1 assessment due to critical impact.

### Objectives

- ✅ Fix slow and refresh-unsafe `/auth/verify` behavior that causes protected pages to flash or redirect incorrectly.
- ✅ Implement optimistic auth state from cookies to prevent race conditions on page refresh.
- ✅ Ensure protected routes can load instantly with cached auth state while revalidating in the background.

### Implementation Summary

**Completed:** October 21, 2025 (as part of Phase 1)

**Performance improvement:** Auth check time reduced from 300ms → <50ms (83% improvement)

**Key changes:**

- Enhanced `authContext.tsx` with optimistic state management and SessionStorage caching
- Created `middleware.ts` for server-side route protection
- Built `<AuthGuard>` component with optimistic rendering option
- Migrated all protected pages to use `<AuthGuard>`
- Added custom auth events for cross-component communication
- **Backend optimization**: Single database query with eager loading

### Technical Details

- **Frontend Optimizations:**
  - Optimistic rendering: Pages load instantly with cached auth state, verify in background
  - Server-side protection: Middleware prevents unauthenticated access to protected routes
  - SessionStorage caching: User data cached for 2 minutes to avoid redundant API calls
  - Event-driven updates: Components react to auth state changes via custom events
  - Backwards compatible: Existing `useAuth()` hook continues to work

- **Backend Optimizations:**
  - Single database query: Auth verification uses one optimized query with join instead of 2-3 separate queries
  - Eager loading: User data loaded in same query as session validation
  - Active user filtering: Database-level filtering for active users only

### Protected Routes Updated

- `/create` (optimistic rendering)
- `/create/[id]` (optimistic rendering)
- `/playlists` (optimistic rendering)
- `/playlist/[id]` (optimistic rendering)
- `/playlist/[id]/edit` (optimistic rendering)
- `/profile` (waits for validation)

---

## Phase 3 – Component Creation & State Decoupling

### Objectives

- Break monolithic components into focused, testable units.
- Establish shared layout wrappers, navigation primitives, and UI atoms.

### Detailed Steps

1. **Refactor `Navigation`**: Split into composable pieces (`Brand`, `DesktopLinks`, `MobileMenu`, `AuthMenu`) and extract menu logic into custom hooks (`useMobileNav`, `useAuthMenu`).
2. **Decompose workflow screens**: In `/create` and `/create/[id]`, isolate mood input, loading states, editor, and results into distinct components with clear contracts.
3. **Extract playlist widgets**: Move repeated track list UI from `PlaylistEditor`, `PlaylistResults`, and `PlaylistCard` into shared subcomponents (e.g., `TrackRow`, `TrackList`, `TrackActions`).
4. **Normalize form primitives**: Reuse components from `src/components/ui` and add any missing ones (Stepper, Tabs) following Tailwind CSS v4 conventions.
5. **Introduce hooks for side effects**: Replace inline `useEffect` logic with named hooks (`useWorkflowSession`, `useAuthRedirect`) and adopt the shared `<AuthGuard>` for protected pages to improve readability and consistency.

### Potential Challenges

- Untangling intertwined state (e.g., workflow session resets triggered by router changes).
- Ensuring extracted components remain type-safe and tree-shakeable.

### Best Practices

- Co-locate component-specific hooks and styles in feature folders.
- Maintain prop-driven interfaces; avoid implicit dependencies on global state.
- Use Storybook-like playgrounds or dedicated demo routes for rapid component iteration (optional but recommended).

---

## Phase 4 – Redundancy Removal & Consistency Hardening

### Objectives

- Eliminate duplicated logic, ensure consistent UX behaviors, and centralize shared concerns.

### Detailed Steps

1. **Workflow state normalization**: Consolidate error handling, loading indicators, and polling logic in `workflowContext` and expose typed helpers.
2. **Reuse marketing sections**: Merge overlapping hero/feature sections across `/` and `/about`, parameterizing content instead of duplicating markup.
3. **Consolidate Spotify auth flows**: Centralize `initiateSpotifyAuth` usage and login guard dialogs to avoid scattered checks.
4. **Unify notifications & toasts**: Replace ad-hoc `toast` usage with a `useToast` helper that enforces consistent copy and severity levels.
5. **Shared utility cleanup**: Move duplicated helpers into `src/lib` (e.g., string formatting, date/time) and write unit tests.
6. **Logging & refresh hygiene**: Strip `console.log` debugging, replace `window.location.reload()` usages with router/state updates, and add a lightweight logger utility for structured diagnostics.

### Potential Challenges

- Some duplication may exist to support divergent visual styles; confirm design alignment before merging.
- Removing redundancy may expose missing edge-case handling.

### Best Practices

- Use codemods or TypeScript references (`find references`) to ensure old implementations are fully removed.
- Document reusable patterns in a “frontend cookbook” section of the repository.

---

## Phase 5 – Performance & Scalability Optimization

### Objectives

- Improve runtime performance, bundle efficiency, and perceived responsiveness.

### Detailed Steps

1. **Bundle analysis**: Run `next build --analyze` and address oversized chunks (e.g., lazy-load DnD Kit where possible, split marketing animations).
2. **Server component adoption**: Migrate static data (marketing content, playlist summaries) to RSCs to reduce client bundle weight.
3. **Memoization & virtualization**: Apply `React.memo`, `useMemo`, and list virtualization (`react-virtualized` or built-in windowing) for large track lists.
4. **Progressive rendering**: Introduce Suspense boundaries and skeleton loaders (leveraging `ui` components) to smooth long-running operations.
5. **Accessibility & UX micro-optimizations**: Ensure focus management, keyboard navigation, and reduced motion support remain intact post-optimization.

### Potential Challenges

- Lazy loading must not break SEO-critical routes or authenticated flows.
- Measuring improvements requires consistent profiling methodology.

### Best Practices

- Check for regressions with automated Lighthouse scripts and React Profiler snapshots.
- Guard dynamic imports with sensible fallbacks and type-safe entry points.

---

## Phase 6 – Testing, QA, and Rollout

### Objectives

- Validate correctness, prevent regressions, and ensure the team can maintain the refactored codebase.

### Detailed Steps

1. **Expand automated testing**: Add unit tests for hooks/utilities, component tests with Playwright/React Testing Library, and end-to-end flow coverage for playlist creation.
2. **Strengthen type safety**: Enforce `strict` TypeScript rules where feasible, introduce discriminated unions for workflow states, and add eslint rules for unused exports.
3. **Visual regression checks**: Capture screenshots for key pages and run visual diff tests before shipping.
4. **Documentation updates**: Refresh `README`, add feature folder READMEs, and document component usage patterns.
5. **Release plan**: Rollout behind feature flags if necessary, monitor error logging (Sentry/console), and collect user feedback.

### Potential Challenges

- Limited existing test coverage may slow confidence building.
- Coordinating rollout with backend changes (if any) requires cross-team communication.

### Best Practices

- Adopt a testing pyramid: heavy unit coverage, focused integration tests, lightweight E2E.
- Automate lint/type/test runs in CI and require them to pass before merging.
- Maintain a changelog summarizing refactor milestones and noteworthy UX adjustments.

---

## Phase Completion Checklist

### Phase 1: Initial Assessment & Discovery ✅ COMPLETED

**Phase 1 Deliverables:**

- ✅ **Deliverables committed and reviewed**: All assessment work completed and documented
- ✅ **Metrics captured pre/post refactor**: Auth performance baseline (300ms) and post-optimization (<50ms) measured
- ✅ **Documentation updated**: Comprehensive CLEANUP_SUMMARY.md, code-cleanup-checklist.md, and refactor docs created
- ✅ **Rollback plan understood**: Auth optimizations are backwards compatible with clear migration path
- ✅ **Centralized configuration**: `src/lib/config.ts`, `src/lib/constants.ts` created
- ✅ **Logging standardization**: `src/lib/utils/logger.ts` implemented with structured logging
- ✅ **API client hardening**: Updated `workflowApi.ts`, `playlistApi.ts`, `pollingManager.ts`, `authContext.tsx`
- ✅ **Auth optimization**: Optimistic rendering, middleware protection, SessionStorage caching (83% improvement)
- ✅ **Console replacement**: `window.location.reload()` patterns replaced with router navigation (6 instances fixed)
- ✅ **Unified loading UI**: LoadingDots component used consistently; custom spinners used appropriately for specific contexts

### Upcoming Phases

For Phase 2 and beyond, confirm the following before proceeding:

- ⏳ Deliverables committed and reviewed.
- ⏳ Metrics captured pre/post refactor where applicable.
- ⏳ Documentation (internal or repo-based) updated.
- ⏳ Rollback plan understood if issues arise.

Following this plan will incrementally modernize the frontend, reduce maintenance cost, and keep user flows stable while unlocking future enhancements.
