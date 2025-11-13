# Performance Optimization Guide: Reducing Workflow Time from 3+ minutes to <2 minutes

## Current Performance Analysis (Based on Real Logs)

**Total Time: 197 seconds (~3.3 minutes)**

```
Breakdown:
├─ Intent analysis: 1.6s (0.8%)
├─ Mood analysis: 2.8s (1.4%)
├─ Orchestration: 186.1s (94.4%) ← MAIN BOTTLENECK
│  ├─ Initial generation: 133.7s (67.8%)
│  │  ├─ Seed gathering: 97.96s
│  │  │  ├─ Anchor selection: 90.88s ← CRITICAL ISSUE
│  │  │  ├─ Artist discovery: 5.65s
│  │  │  ├─ Fetch top tracks: 0.28s
│  │  │  └─ Build seed pool: 0.98s
│  │  └─ Recommendation generation: 35.7s
│  ├─ Iterative improvement: 48.7s (24.7%) ← UNNECESSARY
│  └─ Final processing: 3.8s
└─ Playlist ordering: 6.7s (3.4%)
```

## Key Bottlenecks Identified

### 1. **Anchor Selection: 90.88 seconds** ⚠️ CRITICAL
- Fetching audio features for 109 tracks
- Multiple throttled batches with API waits
- LLM scoring phase adds overhead

### 2. **Iterative Improvement: 48.7 seconds** ⚠️ UNNECESSARY
- Quality was already 0.77 (above 0.75 threshold)
- Full regeneration cycle for minimal improvement
- filter_and_replace strategy generated 45+ new tracks

### 3. **Spotify Rate Limiting: 20+ seconds** ⚠️ INEFFICIENT
- Multiple "waiting 20.2s" messages
- get_artist_top_tracks hitting rate limits
- 8 artists being fetched sequentially

## Recommended Optimizations

### Phase 1: Quick Wins (Target: Save 60-80 seconds)

#### 1.1 Skip Iterative Improvement When Quality is Good
**File:** `backend/app/agents/recommender/orchestrator/orchestrator_agent.py`

```python
# Line ~167: Add early exit check
async def perform_iterative_improvement(self, state: AgentState) -> Dict[str, Any]:
    """Perform iterative improvement loop with convergence detection."""
    
    # OPTIMIZATION: Skip iteration if quality is already good
    quick_eval = await self.quality_evaluator.evaluate_playlist_quality(state)
    if quick_eval['overall_score'] >= 0.75 and quick_eval['cohesion_score'] >= 0.65:
        logger.info(
            f"✓ Skipping iteration - quality already excellent "
            f"(overall: {quick_eval['overall_score']:.2f}, cohesion: {quick_eval['cohesion_score']:.2f})"
        )
        state.metadata["orchestration_iterations"] = 0
        state.metadata["quality_scores"] = [quick_eval]
        return quick_eval
    
    # ... rest of existing code
```

**Expected Savings: ~45-50 seconds**

#### 1.2 Reduce Anchor Candidate Pool
**File:** `backend/app/agents/recommender/mood_analyzer/anchor_selection/selection_engine.py`

```python
# Line ~156: Reduce genre limit from 8 to 4
genre_task = self._get_genre_based_candidates(
    genre_keywords[:4],  # Reduced from 8
    target_features, access_token, mood_prompt, temporal_context,
    skip_audio_features=True
)
```

**File:** `backend/app/agents/recommender/mood_analyzer/anchor_selection/artist_processor.py`

```python
# Reduce artists processed from 8 to 5
MAX_ARTISTS_TO_PROCESS = 5  # Changed from 8
```

**Expected Savings: ~20-30 seconds**

#### 1.3 Reduce Artist Discovery Breadth
**File:** `backend/app/agents/recommender/mood_analyzer/discovery/artist_discovery.py`

```python
# Reduce genre search artist limit from 40 to 20
async def _search_artists_by_genre(self, genre: str, limit: int = 20):  # Changed from 40
```

**Expected Savings: ~5-10 seconds**

### Phase 2: Advanced Optimizations (Target: Save 15-25 seconds)

#### 2.1 Parallel Artist Top Tracks Fetching
**File:** `backend/app/agents/tools/spotify/tools/artist_search.py`

Increase batch parallelism:
```python
# Increase concurrent artist fetches
async def batch_get_artist_top_tracks(self, artist_ids: List[str], ...):
    # Process in batches of 10 instead of 5
    batch_size = 10  # Increased from 5
```

**Expected Savings: ~10-15 seconds**

#### 2.2 Skip LLM Scoring for Anchors (Use Heuristics)
**File:** `backend/app/agents/recommender/mood_analyzer/anchor_selection/selection_engine.py`

Add a fast mode:
```python
# Add fast_mode parameter
async def select_anchor_tracks(
    self,
    # ... existing params ...
    fast_mode: bool = True  # NEW: Skip LLM scoring
):
    if fast_mode:
        # Use fallback (heuristic-based) selection
        return await self._fallback_anchor_selection(...)
    else:
        # Use LLM-driven selection (slower but more accurate)
        return await self._llm_driven_anchor_selection(...)
```

**Expected Savings: ~10-15 seconds**

#### 2.3 Optimize Playlist Ordering
**File:** `backend/app/agents/recommender/playlist_orderer/ordering_agent.py`

Reduce batch analysis overhead:
```python
# Process in larger batches
async def analyze_energy_characteristics(self, ...):
    batch_size = 16  # Increased from 8
```

**Expected Savings: ~3-5 seconds**

### Phase 3: Configuration Changes (No Code Changes)

#### 3.1 Environment Variable Overrides

Add to `.env` or configuration:
```bash
# Performance Mode Settings
FAST_MODE=true
SKIP_ITERATION_IF_QUALITY_GOOD=true
MAX_ITERATIONS=1  # Reduced from 2
QUALITY_THRESHOLD=0.70  # More lenient (was 0.65)
ANCHOR_SELECTION_LIMIT=4  # Reduced from 5
MAX_ARTISTS_FOR_DISCOVERY=20  # Reduced from 40
```

## Implementation Priority

### Immediate (Deploy First)
1. ✅ Skip iterative improvement when quality > 0.75 (saves ~45s)
2. ✅ Reduce anchor candidate pool to 50 tracks (saves ~20s)
3. ✅ Reduce artist discovery breadth (saves ~10s)

**Total Expected Savings: ~75 seconds → Target time: ~120 seconds (2 minutes)**

### Short-term (Deploy Within Week)
4. Parallel artist fetching optimizations (saves ~10s)
5. Skip LLM scoring for anchors in fast mode (saves ~10s)
6. Optimize playlist ordering (saves ~5s)

**Total Expected Savings: ~100 seconds → Target time: ~95 seconds (1.5 minutes)**

### Long-term (Continuous Improvement)
- Implement request deduplication for RecoBeat
- Add multi-tier caching (memory + Redis)
- Optimize database queries
- Implement partial result streaming

## Monitoring & Validation

After implementing optimizations, monitor these metrics:

1. **Average workflow duration** - Target: <120 seconds
2. **Cache hit rate** - Target: >80% on subsequent runs
3. **API call counts** - Target: <200 total API calls
4. **User satisfaction** - Target: No quality degradation

## Testing Strategy

1. **A/B Testing**: Run 50% of workflows with optimizations
2. **Quality Metrics**: Track cohesion scores before/after
3. **User Feedback**: Monitor playlist save rates
4. **Performance Logs**: Compare step timings

## Rollback Plan

If quality degrades:
1. Revert quality threshold to 0.65
2. Re-enable iterative improvement for all workflows
3. Increase anchor candidate pool back to 109 tracks
4. Monitor for 24 hours before re-attempting optimizations
