# Anchor Track Flow Analysis

## Overview

Analysis of the new anchor-first recommendation flow based on workflow log `2d6014cf-4442-4075-aa28-3050a75a6a25` from user prompt: "I like Laufey, especially From the Start and Dreamer".

**Date:** October 17, 2025  
**Status:** ✅ Flow working as designed, improvements identified

---

## What's Working

### 1. Anchor Track Selection ✅

**User-mentioned tracks were correctly identified:**

- "From The Start" by Laufey (0.95 confidence)
- "Dreamer" by Laufey (0.95 confidence)

Both explicitly mentioned tracks were captured and added to the playlist with high confidence scores.

**Genre-based tracks were also added:**

- "Young, Gifted and Black" by Aretha Franklin
- "I Found a Million Dollar Baby" by The Boswell Sisters
- "Santai" by NonaRia

**Total anchor tracks:** 5/5 selected successfully

### 2. Flow Order ✅

The reordered flow executed correctly:

1. Initial mood analysis extracted genres and artists
2. Anchor tracks selected BEFORE full mood analysis
3. Artists discovered using both initial analysis and anchor track artists
4. Full mood analysis completed with anchor context
5. Features extracted and playlist generated

### 3. Anchor Tracks in Final Playlist ✅

All 5 anchor tracks appear in the final recommendations list with proper metadata:

- Source: `"anchor_track"`
- Confidence: 0.95 (highest tier)
- Properly sorted with other recommendations

---

## Issues Identified

### Issue #1: User-Mentioned Tracks Flagged as Outliers

**Problem:**  
Even though the user explicitly said "I like Laufey, especially From the Start and Dreamer", these tracks were marked as quality issues:

**From workflow log (lines 1251-1330):**

```json
{
  "overall_score": 0.67,
  "cohesion_assessment": "moderate_cohesion",
  "outlier_tracks": [
    {
      "track_id": "5JKt1kMrbP4TYbIMM0u4Mz",
      "name": "Santai",
      "artist": "NonaRia",
      "reason": "feels out of place because it is a non-English Indonesian track..."
    },
    {
      "track_id": "4cWQNMHepaisKDPC6ULGxt", 
      "name": "Young, Gifted and Black",
      "artist": "Aretha Franklin",
      "reason": "feels out of place because it is a high-energy soul/R&B song..."
    }
  ],
  "weak_matches": [
    {
      "track_id": "4ZCv7d5Ex3RVdKKPYj764F",
      "name": "Dreamer",
      "artist": "Laufey",
      "cohesion_score": 0.32,
      "reasoning": "The track feels slightly disconnected..."
    }
  ]
}
```

**Impact:**

- "Dreamer" scored only 0.32 cohesion despite explicit user preference
- Quality evaluator doesn't distinguish between user-mentioned and genre-based anchors
- Risk of filtering out user's favorite tracks in iterative improvement

### Issue #2: Genre-Based Anchors Missing Cultural Context

**Problem:**  
Genre-based anchor selection found tracks that match audio features but not stylistic/cultural context:

1. **"Santai" by NonaRia** - Indonesian language track
   - Matches: tempo, energy, valence
   - Misses: language, cultural style, user expectation

2. **"Young, Gifted and Black" by Aretha Franklin** - High-energy soul
   - Matches: genre tags (soul, jazz-adjacent)
   - Misses: intensity level (too energetic for "warm jazz-pop")

**Root cause:**

- Audio features alone aren't enough for genre anchor selection
- No language/region filtering
- Popularity/mainstream appeal not weighted heavily enough

### Issue #3: Quality Evaluation Doesn't Account for User Intent

**Problem:**  
The quality evaluator judges all tracks by cohesion metrics without considering:

- User explicitly mentioned these tracks
- Anchor tracks serve as feature reference, not just playlist inclusions
- Different types of anchors have different purposes

**Current behavior:**

```python
# Quality evaluator treats all tracks equally
for track in recommendations:
    score = calculate_cohesion(track, target_features)
    if score < threshold:
        mark_as_outlier(track)
```

**Needed behavior:**

```python
# Should respect anchor track priority
for track in recommendations:
    if track.source == "anchor_track" and track.user_mentioned:
        # Skip quality filtering for user-mentioned tracks
        continue
    score = calculate_cohesion(track, target_features)
    if score < threshold:
        mark_as_outlier(track)
```

---

## Recommendations

### Priority 1: Protect User-Mentioned Tracks (CRITICAL)

**Objective:** User-mentioned tracks should never be filtered as outliers.

**Implementation:**

1. Add `user_mentioned` flag to anchor track metadata
2. Update quality evaluator to skip cohesion checks for user-mentioned tracks
3. Update improvement strategy to never remove user-mentioned tracks

**Files to modify:**

- `backend/app/agents/recommender/mood_analyzer/anchor_track_selector.py`
- `backend/app/agents/recommender/orchestrator/quality_evaluator.py`
- `backend/app/agents/recommender/orchestrator/improvement_strategy.py`

**Code changes:**

```python
# In anchor_track_selector.py
def _get_user_mentioned_candidates(self, ...):
    # ... existing logic ...
    for track in user_tracks:
        track["user_mentioned"] = True  # Mark as user-mentioned
        track["confidence"] = 1.0  # Maximum confidence
```

```python
# In quality_evaluator.py
def identify_outliers(self, tracks, ...):
    outliers = []
    for track in tracks:
        # Skip user-mentioned tracks
        if track.get("metadata", {}).get("user_mentioned"):
            continue
        # ... existing outlier logic ...
```

### Priority 2: Separate Anchor Track Types (HIGH)

**Objective:** Distinguish between user anchors (guaranteed playlist inclusions) and genre anchors (feature reference only).

**Proposed approach:**

**Two types of anchors:**

1. **User Anchors** - Explicitly mentioned tracks
   - Always included in final playlist
   - Never filtered by quality evaluator
   - Used for feature reference
   - High confidence (1.0)

2. **Genre Anchors** - Discovered from genre searches
   - Used primarily for feature reference
   - Can be filtered if they don't fit cohesion
   - May or may not appear in final playlist
   - Standard confidence (0.75-0.95)

**Implementation:**

```python
# In anchor_track_selector.py
def select_anchor_tracks(self, ...):
    user_anchors = await self._get_user_mentioned_candidates(...)
    genre_anchors = await self._get_genre_based_candidates(...)
    
    # Mark types differently
    for track in user_anchors:
        track["anchor_type"] = "user"
        track["confidence"] = 1.0
        track["protected"] = True  # Never filter
    
    for track in genre_anchors:
        track["anchor_type"] = "genre"
        track["confidence"] = 0.85
        track["protected"] = False  # Can filter if poor fit
    
    return user_anchors + genre_anchors[:limit-len(user_anchors)]
```

**State metadata structure:**

```python
state.metadata["anchor_tracks"] = {
    "user": [...],     # User-mentioned tracks (protected)
    "genre": [...],    # Genre-based tracks (reference only)
}
```

### Priority 3: Improve Genre Anchor Selection (MEDIUM)

**Objective:** Genre-based anchors should better match cultural/stylistic context, not just audio features.

**Improvements needed:**

1. **Add language filtering**

   ```python
   # Prefer English tracks for English prompts
   if prompt_language == "en" and track_language != "en":
       score *= 0.5  # Penalize non-English
   ```

2. **Weight artist popularity higher**

   ```python
   # Prefer mainstream artists for mainstream genres
   popularity_weight = 0.3  # Currently not weighted
   final_score = feature_score * 0.7 + popularity * popularity_weight
   ```

3. **Use more genres for diversity**

   ```python
   # Currently: top 3 genres
   # Proposed: top 5 genres with weighted selection
   genres_to_search = mood_analysis.genre_keywords[:5]
   ```

4. **Add market/region filtering**

   ```python
   # Filter by user's Spotify market
   if user_market and track_markets:
       if user_market not in track_markets:
           score *= 0.7  # Penalize unavailable tracks
   ```

**Files to modify:**

- `backend/app/agents/recommender/mood_analyzer/anchor_track_selector.py`

### Priority 4: Update Quality Evaluation Criteria (MEDIUM)

**Objective:** Quality evaluator should consider different track types and purposes.

**Proposed changes:**

1. **Track type awareness**

   ```python
   def evaluate_quality(self, tracks):
       for track in tracks:
           track_type = track.get("source")
           
           if track_type == "anchor_track":
               if track.get("user_mentioned"):
                   # User-mentioned: skip evaluation
                   track["quality_score"] = 1.0
                   continue
               else:
                   # Genre anchor: lighter evaluation
                   threshold = 0.5  # More lenient
           else:
               # Regular recommendation: normal evaluation
               threshold = 0.65
   ```

2. **Cohesion scoring adjustments**

   ```python
   # Current: Absolute cohesion score
   # Proposed: Relative to anchor tracks
   
   anchor_features = get_average_features(user_anchor_tracks)
   for track in recommendations:
       # Score against user anchors, not just target features
       cohesion = calculate_similarity(track.features, anchor_features)
   ```

3. **Consider user intent in prompt**

   ```python
   # If user says "like X", prioritize similarity to X
   # If user says "energetic", prioritize feature matching
   
   if prompt_has_explicit_tracks(mood_prompt):
       weight_anchor_similarity = 0.7
       weight_feature_matching = 0.3
   else:
       weight_anchor_similarity = 0.4
       weight_feature_matching = 0.6
   ```

**Files to modify:**

- `backend/app/agents/recommender/orchestrator/quality_evaluator.py`
- `backend/app/agents/recommender/orchestrator/improvement_strategy.py`

---

## Implementation Plan

### Phase 1: Critical Fixes (This Week)

**Effort:** 1-2 days

- [ ] Add `user_mentioned` flag to anchor track metadata
- [ ] Update quality evaluator to skip user-mentioned tracks
- [ ] Update improvement strategy to protect user-mentioned tracks
- [ ] Add unit tests for user-mentioned track protection
- [ ] Update logging to show anchor track types

**Success criteria:**

- User-mentioned tracks never appear in outlier lists
- Quality evaluator logs show "Skipping evaluation for user-mentioned track"
- Integration test: user prompt with explicit tracks → those tracks in final playlist

### Phase 2: Anchor Type Separation (Next Week)

**Effort:** 2-3 days

- [ ] Refactor anchor track selector to return two lists
- [ ] Update state metadata structure to separate user/genre anchors
- [ ] Modify recommendation processor to handle anchor types
- [ ] Update quality evaluator to handle genre anchors differently
- [ ] Add confidence levels for different anchor types

**Success criteria:**

- State clearly shows `anchor_tracks.user` and `anchor_tracks.genre`
- Genre anchors can be filtered, user anchors cannot
- Logs distinguish between anchor types

### Phase 3: Genre Anchor Improvements (Later)

**Effort:** 3-4 days

- [ ] Add language detection and filtering
- [ ] Implement popularity weighting in scoring
- [ ] Expand genre search to top 5 genres
- [ ] Add market/region filtering
- [ ] Tune scoring weights based on test cases

**Success criteria:**

- Genre anchors better match cultural context
- Fewer non-English tracks for English prompts
- Higher-quality genre-based recommendations

### Phase 4: Quality Evaluation Refinement (Future)

**Effort:** 3-5 days

- [ ] Implement relative cohesion scoring against user anchors
- [ ] Add prompt intent detection (explicit tracks vs. mood-only)
- [ ] Tune thresholds for different track types
- [ ] Add diversity metrics to quality evaluation
- [ ] Create comprehensive test suite

**Success criteria:**

- Quality scores reflect user intent
- Cohesion measured relative to user preferences
- Fewer false positives in outlier detection

---

## Testing Strategy

### Unit Tests

```python
# Test user-mentioned track protection
def test_user_mentioned_tracks_never_filtered():
    tracks = [
        {"id": "1", "user_mentioned": True, "cohesion": 0.2},  # Poor cohesion
        {"id": "2", "user_mentioned": False, "cohesion": 0.2},  # Poor cohesion
    ]
    
    outliers = quality_evaluator.identify_outliers(tracks)
    
    # User-mentioned track should NOT be in outliers
    assert "1" not in [t["id"] for t in outliers]
    # Regular track should be in outliers
    assert "2" in [t["id"] for t in outliers]

# Test anchor type separation
def test_anchor_types_separated():
    result = anchor_selector.select_anchor_tracks(
        genre_keywords=["indie", "folk"],
        mood_prompt="I love Bon Iver's Holocene",
        artist_recommendations=["Bon Iver"],
        ...
    )
    
    assert "user" in result
    assert "genre" in result
    assert len(result["user"]) > 0  # Found user-mentioned track
    assert result["user"][0]["track_name"] == "Holocene"
```

### Integration Tests

```python
# Test end-to-end flow with explicit tracks
async def test_explicit_track_in_final_playlist():
    state = await workflow_manager.start_workflow(
        mood_prompt="I like Laufey, especially From the Start",
        user_id="test_user"
    )
    
    # Wait for completion
    final_state = await wait_for_completion(state.session_id)
    
    # Verify explicit track is in final playlist
    track_names = [t["name"] for t in final_state.recommendations]
    assert "From the Start" in track_names
    
    # Verify it wasn't marked as outlier
    outliers = final_state.metadata.get("outlier_tracks", [])
    assert "From the Start" not in [t["name"] for t in outliers]
```

### Manual Test Cases

1. **Explicit single track**
   - Prompt: "I love Holocene by Bon Iver"
   - Expected: Holocene appears in playlist, never filtered

2. **Explicit multiple tracks**
   - Prompt: "Make a playlist like Ocean Eyes and lovely by Billie Eilish"
   - Expected: Both tracks in playlist, high confidence

3. **Genre only (no explicit tracks)**
   - Prompt: "Upbeat indie rock"
   - Expected: Genre anchors selected, can be filtered if poor fit

4. **Mixed explicit + mood**
   - Prompt: "Energetic workout music like Till I Collapse"
   - Expected: "Till I Collapse" protected, other tracks match energy

---

## Metrics to Track

### Before Improvements

- User-mentioned tracks filtered as outliers: **Yes** (Issue #1)
- Genre anchors with poor cultural fit: **2/3** (Issue #2)
- Quality evaluation respects user intent: **No** (Issue #3)

### After Phase 1

- User-mentioned tracks filtered as outliers: **0** ✅
- Quality evaluator protection rate: **100%** for user-mentioned
- User satisfaction with explicit track requests: **TBD**

### After All Phases

- Genre anchor cultural fit: **>90%** match expected style
- Outlier false positive rate: **<5%** (currently ~20%)
- User-mentioned track inclusion: **100%** in final playlists
- Genre anchor diversity: **5+ genres** searched (currently 3)

---

## Related Documentation

- [Anchor Track Flow Reorder Summary](../../FLOW_REORDER_SUMMARY.md)
- [Flow Example: Chill Indie Folk](../../FLOW_EXAMPLE.md)
- [Recommendation Improvements Summary](../../RECOMMENDATION_IMPROVEMENTS_SUMMARY.md)

---

## Notes & Open Questions

### Questions for Discussion

1. **Should genre anchors appear in final playlist at all?**
   - Pro: Provides diverse recommendations beyond user's explicit mentions
   - Con: Can introduce poor fits (as seen with Indonesian track)
   - Proposed: Make it configurable, default to feature-reference-only

2. **What's the ideal ratio of user anchors to genre anchors?**
   - Current: Up to 5 total, no ratio enforcement
   - Proposed: Unlimited user anchors + up to 5 genre anchors

3. **Should we use anchor audio features for mood analysis?**
   - Currently: Only use track names in prompt enhancement
   - Potential: Pass actual audio features to influence target feature extraction

4. **How to handle conflicting user preferences?**
   - Example: "I like both Metallica and Laufey"
   - Current behavior: Will likely produce incoherent playlist
   - Potential: Detect conflicts, ask for clarification

### Future Enhancements

1. **Anchor track diversity enforcement**
   - Ensure anchors span different energy levels
   - Prevent all anchors from same artist

2. **Anchor feedback loop**
   - Let users rate anchors in UI
   - Use ratings to improve future anchor selection

3. **Contextual anchor selection**
   - Time of day → energy level preferences
   - Activity type → tempo/valence adjustments

4. **Multi-pass anchor refinement**
   - Initial anchors → features → better anchor search
   - Iteratively improve anchor quality

---

**Last Updated:** October 17, 2025  
**Author:** AI Analysis of Workflow Log  
**Status:** Recommendations pending review and implementation
