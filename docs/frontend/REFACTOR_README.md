# Frontend Refactor Documentation

This directory contains comprehensive documentation for refactoring the MoodList frontend application.

## Documents

### 1. [Frontend Refactor Plan](./frontend-refactor-plan.md)
**The high-level strategic roadmap** for refactoring the frontend codebase.

**Key Contents:**
- 6 phased approach (Phase 1-6, plus critical Phase 2.5 for auth)
- Objectives, challenges, and best practices for each phase
- Phase completion checklists
- Guiding principles for incremental delivery

**When to use:** Start here to understand the overall strategy and sequencing of the refactor.

### 2. [Frontend Refactor Implementation Guide](./frontend-refactor-implementation-guide.md)
**The detailed technical companion** with code examples and patterns for each phase.

**Key Contents:**
- Component complexity analysis and scoring
- Proposed folder structure and architecture
- Before/after code examples for major refactors
- Specific implementation patterns (hooks, components, contexts)
- Testing strategies and success metrics
- Migration checklists with actionable items

**When to use:** Reference this during implementation to see concrete examples and patterns.

### 3. [Code Cleanup Checklist](./code-cleanup-checklist.md)
**Targeted list of tactical cleanups** uncovered during planning.

**Key Contents:**
- Console logging & reload hygiene tasks
- Loading indicator consolidation
- Config/magic number centralization
- Error handling and TypeScript improvements
- Quick wins prioritized by effort & impact

**When to use:** Use this as a punch-list for cleanup work alongside larger refactor phases.

## Critical Issue: Auth Performance

### Problem
The current `/auth/verify` endpoint is:
- **Slow**: 200-500ms network latency on every page mount
- **Race-prone**: Page refreshes cause incorrect redirects because auth verification completes after page logic runs
- **Redundant**: Multiple components trigger separate verification flows

### Impact
- Protected pages (`/playlists`, `/create`, `/playlist/[id]`) flash or kick users out on refresh
- Poor perceived performance
- Confusing UX when navigating between protected routes

### Solution (Phase 2.5)
**Immediate priorities:**
1. **Optimistic auth state** - Trust session cookies initially, verify in background
2. **SessionStorage caching** - Cache user data for 2 minutes to avoid redundant API calls
3. **Next.js middleware** - Server-side cookie checks to prevent unauthorized page loads
4. **`<AuthGuard>` component** - Standardized wrapper for protected routes with configurable loading behavior

**Expected improvements:**
- Auth check: 300ms → <50ms (optimistic render)
- Zero flashing on refresh for authenticated users
- Consistent auth UX across all protected routes

See **Phase 2.5** in both documents for complete implementation details.

## Refactor Phases Overview

| Phase | Focus | Priority | Estimated Effort |
|-------|-------|----------|------------------|
| **1** | Assessment & Discovery | High | 1 week |
| **2** | Architecture & Strategy | High | 1 week |
| **2.5** | **Auth Optimization (CRITICAL)** | **Urgent** | **3-5 days** |
| **3** | Component Decomposition | High | 2-3 weeks |
| **4** | Redundancy Removal | Medium | 1-2 weeks |
| **5** | Performance Optimization | Medium | 1-2 weeks |
| **6** | Testing & Rollout | High | 1-2 weeks |

**Total estimated time:** 8-12 weeks (can be parallelized across team)

## Quick Start for Developers

### If you're working on auth issues:
1. Read **Phase 2.5** in `frontend-refactor-plan.md`
2. Review implementation details in `frontend-refactor-implementation-guide.md` (section 2.5)
3. Start with optimistic cookie checking in `authContext.tsx`
4. Add middleware for server-side protection
5. Build `<AuthGuard>` component
6. Migrate protected pages one at a time

### If you're refactoring components:
1. Check **Phase 1** assessment to understand current pain points
2. Review **Phase 2** architecture proposals for target structure
3. Follow **Phase 3** patterns for decomposition
4. Reference code examples in implementation guide (sections 3.1-3.3)

### If you're improving performance:
1. Run baseline metrics from **Phase 1** (section 1.3)
2. Follow **Phase 5** optimization strategies
3. Use patterns from implementation guide (sections 5.1-5.4)
4. Compare before/after bundle sizes and render times

## Key Architectural Decisions

### Component Organization
```
src/
├── components/
│   ├── layout/      # App-wide (Navigation, Footer)
│   ├── features/    # Business logic (auth, mood, workflow, playlist)
│   ├── marketing/   # Landing pages
│   └── ui/          # Primitives (shadcn/ui style)
├── lib/
│   ├── contexts/    # React contexts (Auth, Workflow)
│   ├── hooks/       # Shared custom hooks
│   ├── api/         # API clients
│   └── utils/       # Pure helpers
```

### State Management
- **Global state**: React Context (auth, workflow)
- **Server state**: Server Components where possible, or client fetch with cache
- **Local state**: Component-level useState/useReducer
- **Future consideration**: TanStack Query for complex data fetching (not required initially)

### Auth Flow (Post Phase 2.5)
```
Middleware (SSR) → Cookie check → Allow/Redirect
    ↓
Client mount → AuthProvider optimistic state from cookie
    ↓
Background verification → Update state if mismatch
    ↓
AuthGuard → Render protected content
```

## Best Practices

### During Refactor
- ✅ Keep main branch deployable after every phase
- ✅ Use feature flags for risky changes
- ✅ Write tests for new patterns before removing old code
- ✅ Document architectural decisions in code comments
- ✅ Run performance benchmarks before/after each phase

### Code Standards
- ✅ TypeScript strict mode
- ✅ Prop-driven component APIs (minimize context dependencies)
- ✅ Co-locate related files (component + hook + types)
- ✅ Consistent naming: `use*` for hooks, `*Context` for contexts
- ✅ Export named exports (better for tree-shaking)

## Success Metrics

Track these throughout the refactor:

| Metric | Baseline | Target | Phase |
|--------|----------|--------|-------|
| Bundle size (client JS) | TBD | -20% | 5 |
| Largest component LOC | 624 | <300 | 3 |
| Auth check time | 300ms | <50ms | 2.5 |
| Test coverage | ~0% | >70% | 6 |
| Lighthouse Performance | TBD | >90 | 5 |
| TypeScript errors (strict) | TBD | 0 | 6 |

## Rollout Strategy

1. **Phase 2.5 (Auth)** - Ship immediately, high impact, low risk
2. **Phases 1-2** - Internal only, planning/documentation
3. **Phase 3** - Behind feature flags, gradual rollout per route
4. **Phases 4-5** - Continuous deployment with monitoring
5. **Phase 6** - Final hardening, remove feature flags

## Questions?

- For strategic decisions: See `frontend-refactor-plan.md`
- For implementation details: See `frontend-refactor-implementation-guide.md`
- For auth issues specifically: Jump to Phase 2.5 in both documents

---

**Last updated:** October 2025  
**Maintained by:** Engineering team  
**Status:** Phase 2.5 auth optimization implemented; Phase 2 architecture in progress (Navigation decomposition, folder normalization next)
