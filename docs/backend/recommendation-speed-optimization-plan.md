# Recommendation Workflow Speed Optimization Plan

## Goal

Reduce recommendation workflow execution time from **~5 minutes to ~1 minute** while maintaining similar quality.

## Current Bottleneck Analysis (Based on Production Logs)

### Real Performance Data (from uvicorn.log)

- **Intent analyzer**: 3.0s ✅
- **Mood analyzer**: 3.1s ✅
- **Seed gatherer**: 114s (1.9 minutes) ⚠️ **MAJOR BOTTLENECK**
- **Recommendation generator**: 67.5s (first pass) + 97.4s (second pass) ⚠️ **BOTTLENECK**
- **Orchestrator**: 100.3s ⚠️ **BOTTLENECK**
- **Total**: ~285 seconds (~4.75 minutes)

### Primary Issue #1: Spotify Rate Limiting (CRITICAL)

- **Problem**: "Rate limit reached for get_artist_top_tracks, waiting 47.8s" - **48 SECOND WAITS!**
- **Impact**: Massive delays during artist discovery phase
- **Frequency**: Multiple occurrences per workflow
- **Location**: `backend/app/agents/tools/agent_tools.py` rate limiting logic
- **Root Cause**: Too many sequential Spotify API calls hitting rate limits

### Primary Issue #2: Reccobeat API Timeout

- **Problem**: Reccobeat API calls take 30-45 seconds, but timeout is set to 30 seconds
- **Impact**: Causes timeout failures, retries, and cascading delays
- **Location**: `backend/app/agents/tools/agent_tools.py:130` (timeout=30s)
- **Frequency**: Multiple calls per workflow (seed chunks, track details, audio features)

### Secondary Issues

1. **Sequential artist processing**: Logs show "Fetching hybrid tracks for artist 1/12", "2/12", etc. - processed one at a time
2. **Sequential seed chunk processing**: Seed chunks processed with delays (0.2s * idx)
3. **Track details fetch**: Separate API call after recommendations to get duration_ms
4. **Limited concurrency**: Only 3 concurrent seed chunk requests
5. **Rate limiting for audio features**: "Rate limit reached for get_track_audio_features, waiting 26.5s"
6. **No request cancellation**: Failed/timeout requests still consume time
7. **Redundant API calls**: Track details fetched separately when could be batched

## Phase 0: Fix Spotify Rate Limiting (CRITICAL - Immediate)

### 0.1 Reduce Spotify API Call Frequency

**Target**: Minimize Spotify API calls to avoid rate limits

**Implementation**:

- Batch artist top tracks requests (currently sequential)
- Increase caching TTL for artist top tracks (currently 30 min → 2 hours)
- Pre-fetch artist data during seed gathering phase
- Use Spotify's batch endpoints where available

**Expected Impact**: Eliminates 48-second waits, saves 50-100s per workflow

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/handlers/artist_pipeline.py`
- `backend/app/agents/tools/spotify_service.py`

### 0.2 Parallelize Artist Processing

**Target**: Process all 12 artists concurrently instead of sequentially

**Current**: Sequential processing (artist 1/12, then 2/12, etc.)
**Change**: Use `asyncio.gather()` to process all artists in parallel with bounded concurrency

**Expected Impact**: Artist processing: 60-80s → 10-15s (75-80% reduction)

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/handlers/artist_pipeline.py`

## Phase 1: Fix Reccobeat Timeout (Immediate - High Impact)

### 1.1 Increase Reccobeat API Timeout

**Target**: Increase timeout from 30s to 60s for Reccobeat-specific tools

**Implementation**:

- Modify `TrackRecommendationsTool.__init__()` to pass `timeout=60`
- Modify `GetMultipleTracksTool.__init__()` to pass `timeout=60`
- Modify `GetTrackAudioFeaturesTool.__init__()` to pass `timeout=60`
- Keep other tools at 30s timeout

**Expected Impact**: Eliminates timeout failures, saves 10-15s per failed request

**Files to Modify**:

- `backend/app/agents/tools/reccobeat/track_recommendations.py:46-55`
- `backend/app/agents/tools/reccobeat/track_info.py` (GetMultipleTracksTool, GetTrackAudioFeaturesTool)
- `backend/app/agents/tools/reccobeat/artist_info.py` (if needed)

### 1.2 Add Request Timeout Monitoring

**Target**: Track actual Reccobeat API response times to identify slow endpoints

**Implementation**:

- Add timing instrumentation to `RateLimitedTool._make_request_internal()`
- Log slow requests (>20s) with endpoint and parameters
- Store metrics in profiling system

**Expected Impact**: Visibility into which endpoints are slowest, data-driven optimization

**Files to Modify**:

- `backend/app/agents/tools/agent_tools.py:503-600`

## Phase 2: Optimize Seed-Based Recommendations (High Impact)

### 2.1 Remove Staggered Delays

**Target**: Eliminate artificial delays between seed chunk processing

**Current**: `await asyncio.sleep(0.2 * idx)` adds 0-2s delays
**Change**: Remove delays, rely on rate limiting and semaphore

**Expected Impact**: Saves 1-3s per workflow

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/generators/seed_based.py:108-118`

### 2.2 Increase Seed Chunk Concurrency

**Target**: Process more seed chunks in parallel

**Current**: 3 concurrent chunks (semaphore limit)
**Change**: Increase to 5-6 concurrent chunks

**Expected Impact**: 40-50% faster seed processing (e.g., 6 chunks: 30s → 15-18s)

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/generators/seed_based.py:127`

### 2.3 Batch Track Details Fetching

**Target**: Fetch track details in parallel batches instead of sequentially

**Current**: `_get_track_details()` called after recommendations, processes all tracks sequentially
**Change**: Batch track IDs into chunks of 50, fetch in parallel with concurrency limit

**Expected Impact**: Track details fetch: 10-15s → 3-5s

**Files to Modify**:

- `backend/app/agents/tools/reccobeat/track_recommendations.py:142-186`

### 2.4 Eliminate Redundant Track Details Call

**Target**: Use duration_ms from recommendation response when available

**Current**: Always calls `/v1/track` endpoint after recommendations
**Change**: Only fetch track details for tracks missing duration_ms in response

**Expected Impact**: Eliminates 5-10s for most requests

**Files to Modify**:

- `backend/app/agents/tools/reccobeat/track_recommendations.py:312-327`

## Phase 3: Parallelize Workflow Steps (Medium-High Impact)

### 3.1 Parallelize Track Details and Audio Features

**Target**: Fetch track details and audio features concurrently

**Current**: Sequential fetching
**Change**: Use `asyncio.gather()` to fetch both in parallel

**Expected Impact**: Saves 5-10s per workflow

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/generators/seed_based.py:141-226`

### 3.2 Pre-fetch Track Details During Recommendation Wait

**Target**: Start fetching track details for known seeds while waiting for recommendations

**Implementation**:

- Extract track IDs from seeds before recommendation call
- Start track details fetch in background
- Use results when recommendations complete

**Expected Impact**: Overlaps 5-10s of work, saves 5-10s total

**Files to Modify**:

- `backend/app/agents/tools/reccobeat/track_recommendations.py:188-412`

### 3.3 Parallelize Seed Chunk and Artist Discovery

**Target**: Start artist discovery while seed chunks are processing

**Current**: Sequential execution in orchestrator
**Change**: Start artist discovery early, overlap with seed processing

**Expected Impact**: Saves 10-20s by overlapping independent work

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/core/engine.py:38-90`

## Phase 4: Aggressive Caching (Medium Impact)

### 4.1 Cache Track Details Aggressively

**Target**: Cache track details with longer TTL (currently 30 min)

**Change**: Increase TTL to 2 hours for track details (tracks don't change frequently)

**Expected Impact**: Reduces track detail API calls by 80-90% for repeat workflows

**Files to Modify**:

- `backend/app/agents/tools/reccobeat/track_recommendations.py:161`

### 4.2 Cache Seed Chunk Results

**Target**: Cache entire seed chunk recommendation results

**Current**: Only caches individual API responses
**Change**: Cache full seed chunk results (recommendations + track details) with 15 min TTL

**Expected Impact**: Instant results for repeated seed combinations

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/generators/seed_based.py:141-226`

### 4.3 Pre-warm Cache for Common Seeds

**Target**: Pre-fetch recommendations for popular seed combinations

**Implementation**: Background job that warms cache for top user seeds

**Expected Impact**: Near-instant results for common requests

**Files to Modify**:

- New file: `backend/app/agents/core/cache_warmer.py`

## Phase 5: Request Optimization (Low-Medium Impact)

### 5.1 Reduce Recommendation Size Per Chunk

**Target**: Request fewer recommendations per chunk, process more chunks in parallel

**Current**: Request 20 recommendations per chunk
**Change**: Request 10-15 per chunk, process 2x chunks in parallel

**Expected Impact**: Faster individual requests, better parallelization

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/generators/seed_based.py:53-87`

### 5.2 Implement Request Cancellation

**Target**: Cancel slow/timeout requests instead of waiting

**Implementation**: Use `asyncio.wait_for()` with timeout, cancel on timeout

**Expected Impact**: Fails fast instead of waiting full timeout period

**Files to Modify**:

- `backend/app/agents/tools/agent_tools.py:253-279`

### 5.3 Circuit Breaker for Reccobeat

**Target**: Skip Reccobeat calls if service is consistently slow/failing

**Implementation**: Track failure rate, open circuit after 3 consecutive failures, retry after 30s

**Expected Impact**: Prevents cascading delays when Reccobeat is down/slow

**Files to Modify**:

- New file: `backend/app/agents/core/circuit_breaker.py`
- `backend/app/agents/tools/reccobeat_service.py:190-275`

## Phase 6: Workflow-Level Optimizations (Low Impact)

### 6.1 Skip Unnecessary Steps

**Target**: Skip playlist ordering if recommendations are already well-ordered

**Implementation**: Check if recommendations meet ordering criteria, skip if yes

**Expected Impact**: Saves 5-10s for well-ordered recommendations

**Files to Modify**:

- `backend/app/agents/workflows/workflow_executor.py:106-124`

### 6.2 Early Exit on Sufficient Recommendations

**Target**: Stop generating recommendations once we have enough high-quality ones

**Current**: Generates full set, then filters
**Change**: Check quality during generation, stop early if threshold met

**Expected Impact**: Saves 10-20s when early recommendations are high quality

**Files to Modify**:

- `backend/app/agents/recommender/recommendation_generator/core/engine.py:38-90`

## Implementation Priority

### Critical Path (Must Do First) ⚡

1. **Phase 0.2**: Parallelize artist processing ⚡ **HIGHEST PRIORITY** (saves 50-70s)
2. **Phase 0.1**: Reduce Spotify API call frequency ⚡ **CRITICAL** (eliminates 48s waits)
3. **Phase 1.1**: Increase Reccobeat timeout to 60s ⚡ **CRITICAL** (prevents timeouts)
4. **Phase 2.2**: Increase seed chunk concurrency to 5-6
5. **Phase 2.4**: Eliminate redundant track details call

### High Impact (Do Next)

6. **Phase 2.1**: Remove staggered delays
7. **Phase 2.3**: Batch track details fetching
8. **Phase 3.1**: Parallelize track details and audio features

### Medium Impact (Nice to Have)

9. **Phase 3.2**: Pre-fetch track details during recommendation wait
10. **Phase 4.2**: Cache seed chunk results
11. **Phase 5.1**: Reduce recommendation size per chunk

### Low Impact (Future Optimization)

12. **Phase 3.3**: Parallelize seed chunk and artist discovery
13. **Phase 4.1**: Increase track details cache TTL
14. **Phase 5.2**: Implement request cancellation
15. **Phase 5.3**: Circuit breaker for Reccobeat

## Expected Performance Improvements

### Baseline: ~4.75 minutes (285s) - **ACTUAL FROM LOGS**

- Intent analysis: 3.0s ✅
- Mood analysis: 3.1s ✅
- Seed gathering: 114s ⚠️ (includes Spotify rate limiting delays)
- Recommendation generation: 67.5s (first pass) + 97.4s (second pass) = 165s ⚠️
  - Seed-based: ~30-40s
  - Artist-based: ~60-80s (sequential processing + rate limits)
  - User anchor: ~5s
- Quality evaluation: ~30s
- Playlist ordering: ~15s
- Overhead/retries: ~50s

### After Phase 0-1 (Critical Path): ~2 minutes (120s)

- Intent analysis: 3s
- Mood analysis: 3s
- Seed gathering: ~50s (reduced Spotify rate limit delays)
- Recommendation generation: ~50s
  - Seed-based: ~20s (no timeouts, better parallelization)
  - Artist-based: ~25s (parallelized, no rate limits)
  - User anchor: ~5s
- Quality evaluation: ~20s
- Playlist ordering: ~10s
- Overhead: ~5s

### After Phase 0-3 (All High Impact): ~1 minute (60s) 🎯

- Intent analysis: 3s
- Mood analysis: 3s
- Seed gathering: ~30s (optimized, cached)
- Recommendation generation: ~30s (fully parallelized)
  - Seed-based: ~10s (optimized chunks, cached)
  - Artist-based: ~15s (parallelized, cached)
  - User anchor: ~5s
- Quality evaluation: ~15s
- Playlist ordering: ~5s (skipped when not needed)
- Overhead: ~2s

### After All Phases: ~1 minute (60s)

- Intent analysis: ~5s
- Mood analysis: ~8s
- Seed gathering: ~30s (with caching)
- Recommendation generation: ~25s (optimized)
  - Seed-based: ~10s (cached + optimized)
  - Artist-based: ~10s
  - User anchor: ~5s
- Quality evaluation: ~10s
- Playlist ordering: ~5s (skipped when not needed)
- Overhead: ~2s

## Risk Assessment

### Low Risk

- Phase 1.1 (Increase timeout): No functional changes, just allows slower responses
- Phase 2.1 (Remove delays): Reduces artificial delays, improves performance
- Phase 4.1-4.2 (Caching): Only improves performance, no functional changes

### Medium Risk

- Phase 2.2 (Increase concurrency): May hit rate limits, monitor closely
- Phase 2.3 (Batch track details): May increase memory usage, test with large batches
- Phase 3.1-3.2 (Parallelization): May expose race conditions, thorough testing needed

### High Risk

- Phase 5.3 (Circuit breaker): May skip Reccobeat when it's just slow, needs careful tuning
- Phase 6.2 (Early exit): May reduce recommendation quality if threshold too low

## Monitoring & Validation

### Key Metrics to Track

1. **Workflow execution time**: P50, P95, P99
2. **Reccobeat API response time**: Per endpoint
3. **Timeout rate**: Percentage of requests timing out
4. **Cache hit rate**: For recommendations and track details
5. **Concurrency utilization**: Active parallel requests
6. **Error rate**: Failed requests per phase

### Success Criteria

- **P95 workflow time**: < 90 seconds
- **P50 workflow time**: < 60 seconds
- **Reccobeat timeout rate**: < 1%
- **Cache hit rate**: > 50% for repeat requests
- **Error rate**: < 2%

### Rollback Plan

Each phase can be rolled back independently:

1. Revert timeout changes (Phase 1.1)
2. Revert concurrency limits (Phase 2.2)
3. Revert parallelization (Phase 3.x)
4. Disable caching (Phase 4.x)

## Timeline Estimate

- **Phase 1**: 2-4 hours (critical fixes)
- **Phase 2**: 4-6 hours (seed optimization)
- **Phase 3**: 4-6 hours (parallelization)
- **Phase 4**: 2-4 hours (caching)
- **Phase 5**: 4-6 hours (request optimization)
- **Phase 6**: 2-4 hours (workflow optimization)

**Total**: 18-30 hours of development + testing

## Next Steps

1. **Immediate**: Implement Phase 1.1 (increase timeout) - blocks all other work
2. **This Week**: Complete Phases 1-2 (critical path + high impact)
3. **Next Week**: Complete Phases 3-4 (parallelization + caching)
4. **Future**: Evaluate Phases 5-6 based on remaining bottlenecks
