# Recommendation Engine Streamlining TODOs

**Estimated total savings: ~1.5 seconds per request**

---

## 🔴 CRITICAL: Deduplication Hell (5+ passes per request)

**Impact**: ~500ms wasted per request
**Complexity**: Medium
**Files affected**:
- `backend/app/agents/recommender/orchestrator/orchestrator_agent.py`
- `backend/app/agents/recommender/orchestrator/recommendation_processor.py`
- `backend/app/agents/recommender/recommendation_generator/core/agent.py`

### Problem
Recommendations are deduplicated **5+ times** in a single request flow:

1. **Iteration loop** (orchestrator_agent.py:216) - Runs 3× for 3 iterations
2. **Final processing** (orchestrator_agent.py:225) - After all iterations
3. **Inside enforce_source_ratio** (recommendation_processor.py:82) - Called during final processing
4. **Inside fill_with_overflow** (recommendation_processor.py:303-304) - Rebuilds dedup sets from scratch
5. **Inside recommendation_generator** (recommendation_generator/core/agent.py:94-310) - On every generation

### Solution
**Keep ONLY ONE deduplication point at the end of the flow:**

```python
# ❌ REMOVE from orchestrator_agent.py:216 (inside improvement loop)
# Line 216: state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)

# ✅ KEEP in orchestrator_agent.py:225 (final processing)
state.recommendations = self.recommendation_processor.remove_duplicates(state.recommendations)

# ❌ REMOVE from recommendation_processor.py:82 (assume input is pre-deduped)
def enforce_source_ratio(self, recommendations, max_count, artist_ratio):
    # recommendations = self.remove_duplicates(recommendations)  # DELETE THIS LINE

# ❌ REMOVE from recommendation_processor.py:303-304 (assume input is pre-deduped)
def fill_with_overflow(self, recommendations, overflow_sources, max_count):
    # seen_track_ids = {rec.track_id for rec in final_recommendations}  # DELETE THESE LINES
    # seen_spotify_uris = {rec.spotify_uri for rec in final_recommendations if rec.spotify_uri}
```

**Additional fix**: Make recommendation_generator return NEW lists instead of appending to state
```python
# recommendation_generator/core/agent.py:94
# Change from: self._deduplicate_and_add_recommendations(final_recommendations, state)
# To: return new recommendations that get merged once at the end
```

---

## 🔴 CRITICAL: Redundant Artist API Calls

**Impact**: ~500ms wasted per request (5 artists × 100ms each)
**Complexity**: Medium
**Files affected**:
- `backend/app/agents/recommender/seed_gatherer/seed_gatherer_agent.py`
- `backend/app/agents/recommender/recommendation_generator/strategies/user_anchor_strategy.py`
- `backend/app/agents/recommender/mood_analyzer/discovery/artist_discovery.py`

### Problem
Same artists are searched **twice** with identical parameters:

1. **First search** in UserAnchorStrategy (user_anchor_strategy.py:373-377):
```python
artist_results = await self.spotify_service.search_spotify_artists(
    access_token=access_token,
    query=artist_name,
    limit=3  # ← Search #1
)
```

2. **Second search** in ArtistDiscovery (artist_discovery.py:261-265):
```python
artists = await self.spotify_service.search_spotify_artists(
    access_token=access_token,
    query=artist_name,
    limit=3  # ← DUPLICATE Search #2!
)
```

### Solution
**Option A**: Cache artist search results in SeedGathererAgent
```python
# In seed_gatherer_agent.py, add:
self._artist_search_cache = {}

# Before calling UserAnchorStrategy or ArtistDiscovery:
artist_results = await self._search_artists_cached(artist_name, access_token)

# Pass cached results to both components
```

**Option B**: Consolidate into single artist search phase
```python
# Have SeedGathererAgent do all artist searches once
# Then pass artist IDs (not names) to downstream components
```

**Option C**: Make UserAnchorStrategy return artist metadata
```python
# UserAnchorStrategy returns both recommendations AND artist metadata
# ArtistDiscovery reuses that metadata instead of re-searching
```

---

## 🟡 MEDIUM: Duplicate Artist Processing Pipelines

**Impact**: Maintenance burden, code duplication
**Complexity**: Medium
**Files affected**:
- `backend/app/agents/recommender/recommendation_generator/generators/artist_based.py`
- `backend/app/agents/recommender/recommendation_generator/strategies/artist_discovery_strategy.py`

### Problem
Two files implement nearly identical workflows:
- Refresh token → derive `tracks_per_artist` → iterate `mood_matched_artists` → `_process_all_artists` → log success/failures

**artist_based.py:42-155** and **artist_discovery_strategy.py:74-179** share ~90% of logic.

### Solution
Extract common pipeline into shared helper:

```python
# Create: backend/app/agents/recommender/recommendation_generator/helpers/artist_pipeline.py

class ArtistRecommendationPipeline:
    """Common pipeline for artist-based recommendation generation."""

    async def process_artists(
        self,
        artists: List[Dict],
        access_token: str,
        target_count: int,
        spotify_service,
        reccobeat_service
    ) -> List[Dict[str, Any]]:
        """Encapsulate token prep, iteration, error handling."""
        # Common logic here
        pass
```

Then both `artist_based.py` and `artist_discovery_strategy.py` use this helper.

---

## 🟡 MEDIUM: Duplicate Ratio Enforcement Logic

**Impact**: Maintenance burden, potential inconsistency
**Complexity**: Low
**Files affected**:
- `backend/app/agents/recommender/recommendation_generator/core/agent.py`
- `backend/app/agents/recommender/orchestrator/recommendation_processor.py`

### Problem
Two implementations of nearly identical ratio enforcement:

1. **RecommendationGeneratorAgent._apply_ratio_limits** (recommendation_generator/core/agent.py:256-286)
   - Splits into anchor/artist/RecoBeat groups
   - Applies 98:2 caps
   - Preserves anchor priority

2. **RecommendationProcessor.enforce_source_ratio** (orchestrator/recommendation_processor.py:65-110)
   - Same grouping, capping, priority ordering
   - Different default ratios and return shapes

### Solution
**Consolidate into single helper** in `RecommendationProcessor`:

```python
# Keep only RecommendationProcessor.enforce_source_ratio
# Delete RecommendationGeneratorAgent._apply_ratio_limits
# Have recommendation_generator call RecommendationProcessor.enforce_source_ratio directly

# In recommendation_generator/core/agent.py:
final_recommendations = self.recommendation_processor.enforce_source_ratio(
    recommendations=processed_recommendations,
    max_count=target_count,
    artist_ratio=0.98  # Pass as parameter
)
```

---

## 🟡 MEDIUM: Duplicate Artist Deduplication/Merge Logic

**Impact**: ~50ms wasted, code duplication
**Complexity**: Low
**Files affected**:
- `backend/app/agents/recommender/mood_analyzer/discovery/artist_discovery.py`
- `backend/app/agents/recommender/seed_gatherer/seed_gatherer_agent.py`

### Problem
Artist deduplication happens in two places with similar logic:

1. **ArtistDiscovery.discover_mood_artists** (artist_discovery.py:42-101)
   - Deduplicates Spotify artist results
   - Stores in `state.metadata["discovered_artists"]`

2. **SeedGathererAgent._discover_and_validate_artists** (seed_gatherer_agent.py:299-345)
   - Repeats similar deduplication when merging user-mentioned + anchor tracks
   - Reimplements `seen_ids` bookkeeping

### Solution
Extract into shared utility:

```python
# Create: backend/app/agents/recommender/utils/artist_utils.py

class ArtistDeduplicator:
    """Shared utility for artist deduplication and merging."""

    @staticmethod
    def merge_and_deduplicate(
        *artist_sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge multiple artist lists and deduplicate by ID."""
        seen_ids = set()
        merged = []
        for artists in artist_sources:
            for artist in artists:
                if artist['id'] not in seen_ids:
                    seen_ids.add(artist['id'])
                    merged.append(artist)
        return merged
```

Then use in both places:
```python
# In artist_discovery.py:
all_artists = ArtistDeduplicator.merge_and_deduplicate(llm_artists, genre_artists)

# In seed_gatherer_agent.py:
all_artists = ArtistDeduplicator.merge_and_deduplicate(
    state.metadata.get("discovered_artists", []),
    user_track_artists,
    anchor_track_artists
)
```

---

## 🟢 LOW: Excessive Per-Track Logging

**Impact**: Log volume, readability
**Complexity**: Very Low
**Files affected**:
- `backend/app/agents/tools/reccobeat/track_info.py`

### Problem
For each audio feature fetch, logs 3 lines:
```
Getting audio features for track {id}
Successfully retrieved audio features for track {id}
Cached audio features for track {id}
```

For 19 tracks = 57 log lines.

### Solution
Replace with batch-level logging:
```python
# Before:
# logger.info(f"Getting audio features for track {track_id}")

# After:
logger.info(f"Fetching audio features for {len(tracks)} tracks in parallel")
# ... fetch all ...
logger.info(f"Successfully fetched {success_count}/{len(tracks)} audio features")
```

---

## 🟢 LOW: Rate Limiting Kills Parallelization

**Impact**: ~15-20 seconds per batch
**Complexity**: Medium (requires API testing)
**Files affected**:
- `backend/app/agents/tools/reccobeat/track_info.py`
- `backend/app/agents/tools/agent_tools.py`

### Problem
1-second minimum interval between requests serializes "parallel" fetches:
```python
# agent_tools.py:486
min_request_interval=1.0  # ← This kills parallelism!
```

Logs show:
```
[debug] Enforcing minimum interval for get_track_audio_features, waiting 1.00s
```
19 times sequentially = 19 seconds!

### Solution
**Option A**: Use batch API endpoint if available
```python
# Instead of individual track requests, use batch:
audio_features = await reccobeat.get_tracks_audio_features([id1, id2, ...])
```

**Option B**: Reduce interval to 0.1s and rely on rate_limit_per_minute
```python
min_request_interval=0.1  # Allow 10 concurrent requests per second
```

**Option C**: Implement request batching at service layer
```python
# Group requests into batches of 5-10 and send together
```

---

## 🟢 LOW: Massive Debug Log Dumps

**Impact**: Unreadable logs
**Complexity**: Very Low
**Files affected**:
- `backend/app/agents/recommender/orchestrator/orchestrator_agent.py` (or wherever this is logged)

### Problem
Entire TrackRecommendation array logged with full objects:
```python
logger.debug(f"enforce_source_ratio recommendations=[TrackRecommendation(...), ...]")
```

Creates multi-kilobyte log entries.

### Solution
Log summary instead:
```python
from collections import Counter

logger.debug(
    f"enforce_source_ratio: {len(recommendations)} tracks, "
    f"sources: {dict(Counter(r.source for r in recommendations))}, "
    f"protected: {sum(1 for r in recommendations if r.protected)}"
)
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Remove 4 of 5 deduplication points
2. ✅ Reduce per-track logging verbosity
3. ✅ Fix debug log dumps

### Phase 2: Core Optimizations (4-6 hours)
4. ✅ Cache artist searches to eliminate redundant API calls
5. ✅ Consolidate ratio enforcement logic
6. ✅ Extract artist deduplication utility

### Phase 3: Architectural Refactor (8-10 hours)
7. ✅ Extract shared artist processing pipeline
8. ✅ Refactor recommendation_generator to return new lists
9. ✅ Investigate rate limiting strategy

---

## Testing Checklist

After each fix:
- [ ] Run full recommendation flow with sample mood prompt
- [ ] Verify final playlist count matches expected
- [ ] Check logs for reduced noise
- [ ] Measure execution time improvement
- [ ] Ensure no duplicate tracks in final output
- [ ] Verify user-mentioned tracks still protected

---

## Measurements (Before/After)

| Metric | Before | Target |
|--------|--------|--------|
| Total execution time | ~38s | ~36s |
| Deduplication passes | 5+ | 1 |
| Artist API calls (5 artists) | 10 | 5 |
| Log lines per request | 2000+ | <1000 |
| Duplicate tracks in output | 0 (after cleanup) | 0 |

---

**Last Updated**: 2025-10-30
**Status**: Ready for implementation
