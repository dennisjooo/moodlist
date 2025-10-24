# Phase 2 Executive Summary

## TL;DR: What's Wrong and How We Fix It

### The Problem (From workflow_62475038-94db-4e8e-ae22-c6ea7a2d0108)

**User said**: "Things like Escape Plan by Travis Scott"

**System gave**:

- ❌ No "Escape Plan" track
- ❌ No Travis Scott at all
- ❌ Indonesian pop, UK R&B, Afrobeat (completely wrong genres)
- ❌ LLM quality score: **0.35/1.0** ("catastrophic failure")

### Why Phase 1 Didn't Fix This

Phase 1 fixed the **metadata propagation** (user_mentioned flags) but didn't fix:

1. **Track search failing** - "Escape Plan" never makes it past the search
2. **Recommendation sources** - 98% from artist discovery (no user anchor strategy)
3. **No quality gates** - Wrong genres get through without validation
4. **Mood Analyzer doing too much** - Selecting anchors, discovering artists, AND analyzing mood

### The Core Issue: Architecture

The current system has **unclear separation of concerns**:

```
Mood Analyzer (overloaded)
├─ Analyze mood features          ✅ Good
├─ Select anchor tracks            ❌ Should be separate
├─ Discover 20+ artists            ❌ Should be separate
└─ Plan playlist                   ✅ Good

Recommendation Generator (limited)
├─ 98% from artist discovery       ⚠️ Too much reliance on one source
├─ 2% from seeds                   ⚠️ Too little from Spotify
└─ No user anchor strategy         ❌ Missing entirely
```

### The Solution: Split Responsibilities

```
┌──────────────────────────────────┐
│ 1. INTENT ANALYZER (NEW)         │ ← Extract what user wants
│    "They want trap, mentioned    │
│     Escape Plan, artist focus"   │
└──────────────────────────────────┘
          ↓
┌──────────────────────────────────┐
│ 2. MOOD ANALYZER (FOCUSED)       │ ← Only audio features
│    "High energy, low acoustic,   │
│     tempo 140-160 BPM"           │
└──────────────────────────────────┘
          ↓
┌──────────────────────────────────┐
│ 3. SEED GATHERER (NEW)           │ ← Find and validate seeds
│    "Found Escape Plan, similar   │
│     tracks, Travis Scott albums" │
└──────────────────────────────────┘
          ↓
┌──────────────────────────────────┐
│ 4. RECOMMENDATION GENERATOR       │ ← Use multiple strategies
│    WITH STRATEGIES:               │
│    - 40% User Anchor Strategy    │ ← NEW: Prioritize user mentions
│    - 40% Artist Discovery        │
│    - 20% Spotify Seeds           │
│                                   │
│    WITH QUALITY GATES:            │
│    - Genre filter (trap only)    │ ← NEW: Block wrong genres
│    - Region filter (no Indo)     │ ← NEW: Block wrong regions
└──────────────────────────────────┘
```

---

## What Each Phase Does

### **Phase 2.1: Intent Analyzer** 🔴 Critical

**Create new agent to understand user intent before doing anything**

Input: "Things like Escape Plan by Travis Scott"

Output:

```json
{
  "intent_type": "artist_focus",
  "user_mentioned_tracks": [
    {"name": "Escape Plan", "artist": "Travis Scott", "priority": "high"}
  ],
  "primary_genre": "trap",
  "genre_strictness": 0.9,
  "exclude_regions": ["indonesian", "southeast_asian"]
}
```

**Why this helps**: Sets clear constraints BEFORE generating recommendations

---

### **Phase 2.2: Refactor Mood Analyzer** 🔴 Critical

**Remove responsibilities that don't belong**

**Remove**:

- ❌ Artist discovery → Move to Seed Gatherer
- ❌ Anchor track selection → Move to Seed Gatherer

**Keep**:

- ✅ Audio feature analysis
- ✅ Color scheme
- ✅ Playlist size planning

**Why this helps**: Clearer separation, easier to debug

---

### **Phase 2.3: Seed Gatherer** 🔴 Critical

**New agent to consolidate all seed/anchor/artist logic**

**Responsibilities**:

1. Search for user-mentioned tracks (Spotify API)
2. Select high-quality anchor tracks
3. Discover relevant artists (8-12, not 20+)
4. Build optimized seed pool

**Why this helps**: One place for all seed logic, easier to fix search issues

---

### **Phase 2.4: User Anchor Strategy** 🟡 High Priority

**New recommendation source that prioritizes user mentions**

**How it works**:

1. Get user-mentioned tracks from Seed Gatherer
2. Call Spotify Recommendations API with ONLY those tracks
3. Fetch artist's top tracks
4. Mark results as high confidence

**New recommendation mix**:

```
40% - User Anchor Strategy     ← NEW: Prioritize user mentions
40% - Artist Discovery
15% - Seed-Based
5%  - RecoBeat fallback
```

**Why this helps**: Direct connection from user mention → recommendations

---

### **Phase 2.5: Genre Consistency Filter** 🟡 High Priority

**Quality gate to block wrong genres**

**Rules**:

```python
if intent.primary_genre == "trap":
    if track.acousticness > 0.3:
        REJECT("Too acoustic for trap")
    
    if artist.language == "indonesian":
        REJECT("Wrong language")
    
    if not artist.genres.overlap(["trap", "hip hop", "rap"]):
        REJECT("Artist genre mismatch")
```

**Why this helps**: Prevents Indonesian pop from getting into trap playlists

---

### **Phase 2.6: Artist Discovery Quality** 🟡 High Priority

**Improve quality of discovered artists**

**Changes**:

- Reduce from 20+ artists → 8-12 artists
- Validate artist genres match mood
- Sample 2-3 tracks per artist to check fit
- Reject artists that don't match

**Why this helps**: Better artists → better recommendations

---

### **Phase 2.7: Smarter Diversity** 🟢 Medium Priority

**Context-aware diversity based on intent**

**Artist Focus Mode**:

```python
if intent.intent_type == "artist_focus":
    max_tracks_per_artist = 5  # Allow more repetition
    penalty_multiplier = 0.3    # Weaker penalties
```

**Genre Exploration Mode**:

```python
if intent.intent_type == "genre_exploration":
    max_tracks_per_artist = 2
    penalty_multiplier = 1.5  # Stronger penalties
```

**Why this helps**: Respects user intent for single-artist playlists

---

### **Phase 2.8: Update Orchestrator** 🔴 Critical

**Wire everything together**

**New flow**:

```python
1. Intent Analyzer     → What does user want?
2. Mood Analyzer       → What audio features?
3. Seed Gatherer       → What seeds/artists?
4. Rec Generator       → Generate with new strategies
5. Quality Evaluator   → Validate earlier in pipeline
```

**Why this helps**: Clear, sequential pipeline

---

### **Phase 2.9: Validation Logging** 🟢 Medium Priority

**Understand why tracks are accepted/rejected**

**Logs for each track**:

```python
logger.info(
    "Track: 'Escape Plan' by Travis Scott",
    confidence=0.95,
    genre_match=0.92,
    decision="ACCEPTED",
    source="user_anchor_strategy"
)

logger.info(
    "Track: 'Seandainya' by Vierra",
    confidence=0.45,
    genre_match=0.12,
    decision="REJECTED",
    rejection_reason="language_mismatch_indonesian"
)
```

**Why this helps**: Easy debugging, understand system decisions

---

## Success Criteria

After Phase 2, for input "Things like Escape Plan by Travis Scott":

✅ **"Escape Plan" MUST be in final playlist**
✅ **Travis Scott tracks dominate (60%+ of playlist)**
✅ **All tracks are trap/hip-hop (no Indonesian pop)**
✅ **LLM quality score > 0.7 (up from 0.35)**
✅ **Average confidence > 0.6 (up from 0.42)**
✅ **No wrong language/region tracks**

---

## Timeline

| Priority | Phases | Time | Dependencies |
|----------|--------|------|--------------|
| 🔴 **Must Do First** | 2.1, 2.2, 2.3, 2.8 | 12-17 hours | None - Core architecture |
| 🟡 **High Impact** | 2.4, 2.5, 2.6 | 8-11 hours | After core is done |
| 🟢 **Nice to Have** | 2.7, 2.9 | 4-6 hours | After high impact |

**Total**: 24-34 hours

**Recommended Approach**: Do critical phases first, test, then add high-impact features

---

## Key Decisions Needed

1. **RecoBeat vs Spotify**: Should we reduce RecoBeat reliance further? (Currently 5% fallback)
2. **User Anchor Ratio**: Is 40% for user anchors the right amount?
3. **Genre Filtering**: Strict (reject) or soft (penalize confidence)?
4. **Artist Discovery**: Should we validate every artist or just the top ones?

---

## Questions?

- **Why not just fix the search?** → Search is part of the problem, but the bigger issue is architectural
- **Can we skip some phases?** → Critical phases (2.1, 2.2, 2.3, 2.8) are minimum for success
- **What if I want only Phase 2.4?** → Won't work without Intent Analyzer and Seed Gatherer providing proper input

---

## Next Steps

1. Review this plan
2. Decide on implementation order
3. Start with Phase 2.1 (Intent Analyzer)
4. Build incrementally, test each phase
5. Validate with real user prompts
