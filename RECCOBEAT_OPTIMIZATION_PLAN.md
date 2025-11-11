# RecoBeat Performance Optimization Plan

## Problem Analysis

### Current Issues
1. **Extreme Slowness**: RecoBeat API requests taking 20-70+ seconds per call
2. **Frequent Timeouts**: 60s timeout being hit regularly
3. **Rate Limiting**: Conservative limits still causing issues
4. **High Volume**: Multiple API calls per workflow for audio features

### Log Evidence
```
[12:15:14] Slow RecoBeat API request: 68.114811s
[12:15:19] Slow RecoBeat API request: 72.997514s
[12:16:13] Slow RecoBeat API request: 46.771105s
[12:18:46] Slow RecoBeat API request: 36.111127s
[12:19:40] Slow RecoBeat API request: 21.727792s
```

### Current RecoBeat Usage
1. **Track recommendations**: Get similar tracks based on seeds + audio features
2. **Audio features**: Get acoustic, energy, tempo, valence for filtering/scoring
3. **ID conversion**: Convert Spotify track IDs ↔ RecoBeat IDs
4. **Track details**: Get track metadata
5. **Artist info**: Search and get artist data

## Optimization Strategy

### Phase 1: Super Aggressive Caching (PRIMARY FIX)

#### Current TTLs
- Audio features: **1 hour** (3,600s)
- Track recommendations: **30 minutes** (1,800s)
- Track details: **Unknown** (likely 1 hour)
- ID mappings: **60 days** (validated), **14 days** (missing)

#### New TTLs (Extremely Aggressive)
- **Audio features**: 1 hour → **90 days** (7,776,000s)
  - Rationale: Audio features are immutable track properties
  - These never change for a given track
  
- **Track recommendations**: 30 minutes → **7 days** (604,800s)
  - Rationale: Recommendations for same seeds+features won't change much
  - Acceptable staleness tradeoff for performance
  
- **Track details**: 1 hour → **30 days** (2,592,000s)
  - Rationale: Track metadata rarely changes
  
- **ID mappings**: 60 days → **180 days** (15,552,000s)
  - Rationale: Spotify↔RecoBeat mapping is immutable
  - Once mapped, stays mapped forever

#### Benefits
- Workflow #2+ will be **dramatically faster** (50-80% time saved)
- RecoBeat API load reduced by 80-90%
- No more 60s+ waits for audio features
- Rate limiting becomes non-issue

### Phase 2: Bidirectional ID Mapping

#### Current State
- Only Spotify ID → RecoBeat ID caching
- Must re-fetch RecoBeat IDs to find Spotify IDs

#### Enhancement
1. **Add reverse cache**: RecoBeat ID → Spotify ID
2. **Dual writes**: When mapping Spotify→RecoBeat, also cache RecoBeat→Spotify
3. **Same 180-day TTL** for both directions
4. **New methods**:
   - `get_spotify_id_from_reccobeat(reccobeat_id)`
   - `bulk_get_spotify_ids(reccobeat_ids)`

#### Benefits
- Can search by either ID type
- Reduces redundant conversion calls
- Enables efficient reverse lookups

### Phase 3: Reduce Unnecessary Calls

#### Optimizations
1. **Skip unknown tracks**: If RecoBeat ID conversion fails, don't try audio features
2. **Better deduplication**: Track in-flight requests globally
3. **Batch more aggressively**: Increase chunk sizes where safe
4. **Early exit**: If cached data available, skip API entirely

#### Implementation
- Add request deduplication at service level
- Improve batch scheduling to minimize API calls
- Use validated ID registry more extensively

### Phase 4: Graceful Degradation

#### Handle Missing Data Better
1. **Default audio features**: Use genre-based defaults when track not in RecoBeat
2. **Skip filtering**: Allow tracks without features to pass through
3. **Continue on failure**: Don't block workflow on audio feature failures
4. **Better logging**: Track which tracks are missing, analyze patterns

#### Benefits
- Workflows complete even with partial RecoBeat availability
- Better UX - fewer failures
- Identify tracks that need manual feature assignment

## Implementation Priority

### HIGH PRIORITY (Immediate)
1. ✅ Increase audio features TTL to 90 days
2. ✅ Increase track recommendations TTL to 7 days
3. ✅ Increase track details TTL to 30 days
4. ✅ Increase ID mapping TTL to 180 days

### MEDIUM PRIORITY (Next)
5. ✅ Add bidirectional ID mapping (RecoBeat→Spotify)
6. ✅ Skip audio features for unconverted tracks
7. ✅ Add default audio features for missing tracks

### LOW PRIORITY (Optional)
8. Better batch scheduling
9. Global request deduplication
10. Analytics on missing tracks

## Expected Impact

### Before Optimization
- First workflow: ~280-300 seconds
- Second workflow: ~280-300 seconds (minimal cache benefit)
- RecoBeat calls: 50-100+ per workflow

### After Optimization
- First workflow: ~280-300 seconds (same - initial cache population)
- Second workflow: ~60-120 seconds (massive cache hit rate)
- Third+ workflows: ~60-120 seconds (sustained performance)
- RecoBeat calls: 5-15 per workflow (80-90% reduction)

### Time Savings
- **Per workflow**: 60-70% reduction after first run
- **RecoBeat load**: 80-90% reduction
- **User experience**: Much snappier, more consistent
- **Rate limiting**: Becomes a non-issue

## Risks & Mitigation

### Risk 1: Stale Data
- **Likelihood**: Low (audio features don't change)
- **Impact**: Low (recommendations still relevant)
- **Mitigation**: Can manually flush cache if needed

### Risk 2: Cache Size
- **Likelihood**: Medium (90-day TTL = lots of data)
- **Impact**: Medium (Redis memory usage)
- **Mitigation**: Monitor Valkey usage, can reduce TTL if needed

### Risk 3: Wrong Mappings
- **Likelihood**: Very Low (IDs are immutable)
- **Impact**: High (wrong track features)
- **Mitigation**: Validate mappings, log mismatches

## Monitoring

### Metrics to Track
1. Cache hit rate for audio features
2. Cache hit rate for ID mappings
3. Average RecoBeat calls per workflow
4. Average workflow duration
5. RecoBeat API latency (P50, P95, P99)
6. Number of tracks with missing features

### Success Criteria
- Cache hit rate >70% after initial runs
- Workflow time <150s for cached data
- RecoBeat calls <20 per workflow
- No increase in errors/failures

## Alternative: Reduce RecoBeat Dependency

### If Caching Isn't Enough
1. **Use Spotify recommendations more**: Less accurate but faster
2. **Pre-compute features**: Offline batch processing
3. **Approximate features**: ML model to estimate from Spotify data
4. **Local database**: Mirror RecoBeat data locally

### Why Not Recommended Now
- Caching should provide 80-90% improvement
- These alternatives are much more complex
- RecoBeat still needed for audio features (Spotify deprecated theirs)
