# Phase 2: Recommendation Quality Overhaul

## Problem Analysis (workflow_62475038-94db-4e8e-ae22-c6ea7a2d0108)

### Critical Issues Identified

1. **Missing User-Mentioned Tracks**
   - User explicitly said: "Things like Escape Plan by Travis Scott"
   - ❌ **"Escape Plan" is NOT in the final recommendations**
   - ❌ **No Travis Scott tracks at all** (despite being explicitly requested)
   - ✅ SZA tracks were included (but user mentioned them less explicitly)

2. **Severe Genre Mismatch**
   - LLM quality assessment: **0.35/1.0** - "catastrophic failure"
   - Recommendations include:
     - Indonesian Pop ("Seandainya" by Vierra)
     - UK R&B ("Escapism." by RAYE)
     - Afrobeat ("One Dance" by Drake)
     - Slowed & Reverb versions (contradicts high-energy mood)
     - Obscure artists (Paye Fox, Big Skeez, Bodega Collective)
   - User wanted: **Aggressive trap like Travis Scott, Future, Metro Boomin**

3. **Architectural Root Causes**
   - **Mood Analyzer is doing too much**:
     - Analyzing mood
     - Selecting anchor tracks
     - Discovering artists
     - Planning playlist targets
     - All before recommendation generation starts

   - **Recommendation Generator has weak control**:
     - Relies on 98% artist discovery, 2% seeds
     - No direct genre/style enforcement
     - No user intent validation
     - Diversity penalties applied too broadly

4. **Quality Issues From Workflow**

   ```json
   "final_quality_evaluation": {
     "overall_score": 0.5407,  // Below 0.8 threshold
     "cohesion_score": 0.6183,
     "confidence_score": 0.4207,  // Very low confidence
     "meets_threshold": false,
     "issues": [
       "Low average confidence: 0.42",
       "Severe genre mismatch",
       "Lack of core expected artists (Travis Scott, Future, Metro Boomin)",
       "Multiple tracks from non-US/English-speaking markets"
     ]
   }
   ```

## Architectural Vision

### Current Flow (Broken)

```
User Prompt
    ↓
Mood Analyzer (Does Everything)
    - Mood analysis
    - Extract user mentions
    - Select anchor tracks
    - Discover artists (20+ artists)
    - Plan playlist
    ↓
Recommendation Generator (Limited Power)
    - 98% from discovered artists
    - 2% from seeds
    - Apply diversity
    ↓
Quality Evaluator
    - Too late to fix issues
```

### Proposed Flow (Better Separation of Concerns)

```
User Prompt
    ↓
┌─────────────────────────────────────┐
│ 1. INTENT ANALYZER (NEW)            │
│    - Extract explicit mentions      │
│    - Identify mood/genre/vibe       │
│    - Detect focus type:             │
│      * Single artist                │
│      * Genre exploration            │
│      * Mood-based variety           │
│    - Set quality constraints        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. MOOD ANALYZER (FOCUSED)          │
│    - Audio feature analysis         │
│    - Color scheme                   │
│    - Playlist size/structure        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. SEED GATHERER (NEW)              │
│    - Search user-mentioned tracks   │
│    - Select anchor tracks           │
│    - Discover key artists           │
│    - Build seed pool (5-10)         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. RECOMMENDATION GENERATOR (SMARTER)│
│    Strategy Selection Based on Intent│
│    ├─ Artist Focus Strategy         │
│    ├─ Genre Exploration Strategy    │
│    ├─ Mood Variety Strategy         │
│    └─ User Anchor Strategy (NEW)    │
│                                      │
│    Quality Gates:                   │
│    - Genre consistency check        │
│    - Artist relevance check         │
│    - Language/region filtering      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 5. QUALITY EVALUATOR (EARLIER)      │
│    - Validate against intent        │
│    - Check for outliers             │
│    - Request regeneration if needed │
└─────────────────────────────────────┘
```

---

## Implementation Plan

### **Phase 2.1: Create Intent Analyzer Agent** (Foundation)

**Goal**: Extract and structure user intent before any recommendation work

#### New Agent: `IntentAnalyzerAgent`

**Location**: `backend/app/agents/recommender/intent_analyzer/`

**Responsibilities**:

1. Extract explicit track/artist mentions
2. Identify intent type (artist focus, genre exploration, mood variety)
3. Set quality constraints (genre strictness, language preferences)
4. Create structured intent profile

**Output Structure**:

```python
{
  "intent_type": "artist_focus" | "genre_exploration" | "mood_variety",
  "user_mentioned_tracks": [
    {"track_name": "Escape Plan", "artist_name": "Travis Scott", "priority": "high"}
  ],
  "user_mentioned_artists": ["Travis Scott", "SZA"],
  "primary_genre": "trap",
  "genre_strictness": 0.9,  # 0-1, how strict to enforce genre
  "language_preference": ["english"],
  "region_preference": ["western"],
  "exclude_regions": ["southeast_asian", "indonesian"],
  "allow_obscure_artists": false,
  "quality_threshold": 0.7
}
```

**Tasks**:

- [ ] Create `intent_analyzer/` directory structure
- [ ] Implement `IntentAnalyzerAgent` class
- [ ] Create LLM prompt for intent extraction
- [ ] Add track/artist mention extraction (reuse from Phase 1)
- [ ] Add intent type classification
- [ ] Add unit tests
- [ ] Update orchestrator to call intent analyzer first

---

### **Phase 2.2: Refactor Mood Analyzer** (Simplification)

**Goal**: Strip out responsibilities that don't belong, focus on audio features

#### Updated: `MoodAnalyzerAgent`

**Keep** (Core responsibilities):

- Audio feature analysis
- Color scheme generation
- Playlist size/target planning
- Feature weights

**Remove** (Move to other agents):

- ❌ Artist discovery → Move to Seed Gatherer
- ❌ Anchor track selection → Move to Seed Gatherer
- ❌ User mention extraction → Already in Intent Analyzer
- ❌ Keyword extraction → Can be in Intent Analyzer

**Tasks**:

- [ ] Remove `AnchorTrackSelector` from `MoodAnalyzerAgent.__init__`
- [ ] Remove `ArtistDiscovery` from `MoodAnalyzerAgent.__init__`
- [ ] Update `execute()` to skip artist/anchor selection
- [ ] Simplify to just mood → features pipeline
- [ ] Update unit tests

---

### **Phase 2.3: Create Seed Gatherer Agent** (Consolidation)

**Goal**: Centralize all seed/anchor/artist discovery logic

#### New Agent: `SeedGathererAgent`

**Location**: `backend/app/agents/recommender/seed_gatherer/`

**Responsibilities**:

1. Search and validate user-mentioned tracks
2. Select high-quality anchor tracks
3. Discover relevant artists
4. Build optimized seed pool (5-10 tracks)

**Input** (from Intent Analyzer + Mood Analyzer):

```python
{
  "intent": {...},  # From Intent Analyzer
  "mood_analysis": {...},  # From Mood Analyzer
  "target_features": {...}
}
```

**Output**:

```python
{
  "user_mentioned_tracks": [
    {"spotify_id": "...", "name": "Escape Plan", "protected": true}
  ],
  "anchor_tracks": [
    {"spotify_id": "...", "name": "Sicko Mode", "anchor_type": "genre"}
  ],
  "discovered_artists": ["Travis Scott", "Future", "Metro Boomin"],
  "seed_pool": ["spotify:track:...", ...]
}
```

**Tasks**:

- [ ] Create `seed_gatherer/` directory structure
- [ ] Move `AnchorTrackSelector` logic here
- [ ] Move `ArtistDiscovery` logic here
- [ ] Implement artist validation (check if they match genre)
- [ ] Add logging for seed selection decisions
- [ ] Add unit tests
- [ ] Update orchestrator to call after mood analysis

---

### **Phase 2.4: Add User Anchor Strategy** (New Recommendation Source)

**Goal**: Prioritize user-mentioned tracks and their direct relatives

#### New Strategy: `UserAnchorStrategy`

**Location**: `backend/app/agents/recommender/recommendation_generator/strategies/user_anchor_strategy.py`

**How It Works**:

1. Get user-mentioned tracks from Seed Gatherer
2. Use Spotify's "Get Recommendations" API with ONLY those tracks as seeds
3. Fetch artist's top tracks
4. Use RecoBeat with high feature weight on user tracks
5. Mark all results as high confidence

**Recommendation Mix** (with User Anchors):

```
40% - User Anchor Strategy (if user mentioned tracks)
40% - Artist Discovery (from key artists)
15% - Seed-Based (genre exploration)
5%  - RecoBeat fallback
```

**Tasks**:

- [ ] Create `UserAnchorStrategy` class
- [ ] Implement Spotify recommendation API call
- [ ] Implement artist top tracks fetch
- [ ] Add confidence boosting for user-anchor results
- [ ] Add to `RecommendationEngine` strategy selection
- [ ] Add unit tests

---

### **Phase 2.5: Add Genre Consistency Filter** (Quality Gate)

**Goal**: Block obviously wrong genres before they reach recommendations

#### New Filter: `GenreConsistencyFilter`

**Location**: `backend/app/agents/recommender/recommendation_generator/filters/genre_filter.py`

**How It Works**:

1. Get primary genre from intent (e.g., "trap")
2. For each track:
   - Fetch artist genres from Spotify
   - Check if artist genres match intent
   - Check audio features (e.g., trap = low acousticness, high energy)
   - Block if mismatch exceeds threshold

**Example Rules**:

```python
if intent.primary_genre == "trap":
    # Block if too acoustic (trap is electronic)
    if track.acousticness > 0.3:
        reject("Too acoustic for trap")
    
    # Block if artist genres don't overlap
    if not any(g in ["rap", "trap", "hip hop"] for g in artist.genres):
        reject("Artist genre mismatch")
    
    # Block if wrong language/region
    if track.language in intent.exclude_regions:
        reject("Wrong language/region")
```

**Tasks**:

- [ ] Create `GenreConsistencyFilter` class
- [ ] Implement genre matching logic
- [ ] Implement audio feature validation
- [ ] Implement region/language filtering
- [ ] Add configurable strictness (from intent)
- [ ] Add to recommendation pipeline
- [ ] Add unit tests

---

### **Phase 2.6: Improve Artist Discovery Quality** (Data Quality)

**Goal**: Only discover artists that actually match the mood/genre

#### Updated: `ArtistDiscovery`

**Current Issues**:

- Discovers 20+ artists
- Many are low-quality or off-genre
- No validation against mood

**Improvements**:

1. **Reduce quantity, increase quality**: 8-12 artists max
2. **Validate artist genres**: Must overlap with mood genres
3. **Check artist popularity**: Optional filter for mainstream vs underground
4. **Sample tracks**: Check 2-3 tracks per artist to validate fit

**Tasks**:

- [ ] Add artist genre validation
- [ ] Add track sampling for validation
- [ ] Reduce discovery count to 8-12
- [ ] Add popularity filtering
- [ ] Add logging for rejected artists
- [ ] Update unit tests

---

### **Phase 2.7: Smarter Diversity Penalties** (Already Partially Done in Phase 1)

**Goal**: Context-aware diversity that respects intent

#### Updated: `DiversityManager`

**Phase 1 Fixes** (Already implemented):

- ✅ Exempt `user_mentioned` tracks from penalties
- ✅ Exempt `protected` tracks from penalties

**Phase 2 Additions**:

- [ ] **Artist Focus Mode**: If intent is "artist_focus", allow more repetition

  ```python
  if intent.intent_type == "artist_focus":
      max_tracks_per_artist = 5  # Instead of 2-3
      penalty_multiplier = 0.3    # Weaker penalties
  ```

- [ ] **Genre Exploration Mode**: Enforce more diversity

  ```python
  if intent.intent_type == "genre_exploration":
      max_tracks_per_artist = 2
      penalty_multiplier = 1.5  # Stronger penalties
  ```

**Tasks**:

- [ ] Add intent-aware diversity rules
- [ ] Update penalty calculation to use intent
- [ ] Add logging for diversity decisions
- [ ] Update unit tests

---

### **Phase 2.8: Update Orchestrator** (Integration)

**Goal**: Wire all agents together in correct order

#### Updated: `RecommendationOrchestrator`

**New Execution Flow**:

```python
async def execute(state: AgentState) -> AgentState:
    # 1. Analyze user intent
    state = await intent_analyzer.execute(state)
    
    # 2. Analyze mood/audio features
    state = await mood_analyzer.execute(state)
    
    # 3. Gather seeds (anchors + artists)
    state = await seed_gatherer.execute(state)
    
    # 4. Generate recommendations (with new strategies)
    state = await recommendation_generator.execute(state)
    
    # 5. Evaluate quality (earlier in pipeline)
    state = await quality_evaluator.execute(state)
    
    # 6. Iterate if quality is poor (existing logic)
    if not state.quality_meets_threshold:
        return await self._improve_and_retry(state)
    
    return state
```

**Tasks**:

- [ ] Add `IntentAnalyzerAgent` to orchestrator
- [ ] Add `SeedGathererAgent` to orchestrator
- [ ] Update execution order
- [ ] Update state passing between agents
- [ ] Add integration tests
- [ ] Update documentation

---

### **Phase 2.9: Add Validation Logging** (Debugging)

**Goal**: Understand why tracks are selected/rejected

**Status**: ✅ **IMPLEMENTED**

#### New Module: `RecommendationLogger`

**Location**: `backend/app/agents/recommender/utils/recommendation_logger.py`

**Implementation Details**:

The `RecommendationLogger` provides comprehensive structured logging for the entire recommendation pipeline:

**Key Features**:
- Session-scoped logging with `session_id` and `workflow_id` binding
- Standardized event taxonomy: `track_evaluation`, `genre_filter`, `diversity_penalty`, `quality_evaluation`, `source_mix`, etc.
- Multi-level logging (INFO for summaries, DEBUG for detailed traces)
- Integration-ready for all pipeline components

**Core Logging Methods**:

```python
# Track evaluation (acceptance/rejection)
rec_logger.log_track_evaluation(
    track_name="Escape Plan",
    artist="Travis Scott",
    confidence=0.95,
    genre_match_score=0.92,
    feature_match_score=0.88,
    decision="ACCEPTED",
    source="user_anchor_strategy"
)

# Genre filtering
rec_logger.log_genre_filter_decision(
    track_name="Seandainya",
    artist="Vierra",
    primary_genre="trap",
    artist_genres=["indonesian pop"],
    passed=False,
    reason="Artist genres don't match trap"
)

# Diversity penalties
rec_logger.log_diversity_penalty(
    track_name="SICKO MODE",
    artist="Travis Scott",
    original_confidence=0.88,
    adjusted_confidence=0.78,
    penalty=0.10,
    artist_count=3,
    is_protected=False
)

# Quality evaluation
rec_logger.log_quality_evaluation(
    overall_score=0.78,
    cohesion_score=0.82,
    confidence_score=0.71,
    diversity_score=0.85,
    meets_threshold=True,
    issues=["2 tracks below 0.5 confidence"],
    outlier_count=2
)

# Source mix analysis
rec_logger.log_recommendation_source_mix(
    user_anchor_count=8,
    artist_discovery_count=8,
    seed_based_count=3,
    fallback_count=1,
    total_count=20
)
```

**Additional Capabilities**:
- Artist discovery tracking
- Strategy generation logging
- Filter statistics
- LLM assessment logging
- Seed gathering logging
- Intent analysis logging (Phase 2.1 ready)
- Pipeline phase summaries

**Usage**:

```python
from app.agents.recommender.utils.recommendation_logger import create_recommendation_logger

# Create logger for workflow
rec_logger = create_recommendation_logger(
    session_id=state.session_id,
    workflow_id=state.metadata.get("workflow_id")
)

# Use throughout pipeline
rec_logger.log_track_evaluation(...)
rec_logger.log_quality_evaluation(...)
```

**Documentation**: See [Phase 2 Logs Implementation Guide](./phase-2-logs-implementation.md) for complete usage examples and integration patterns.

**Tasks**:

- [x] Create `RecommendationLogger` class
- [x] Add event taxonomy and structured fields
- [x] Implement all logging methods (10+ methods)
- [x] Add factory function for easy instantiation
- [x] Create comprehensive documentation
- [ ] Add structured logging to all recommendation strategies
- [ ] Add logging to filters
- [ ] Add logging to diversity manager
- [ ] Integrate with quality evaluator
- [x] Create log analysis script (`backend/scripts/analyze_recommendation_logs.py`)

---

## Testing Strategy

### Test Scenarios

#### Scenario 1: Explicit Track Mention

```
Input: "Things like Escape Plan by Travis Scott"
Expected:
- ✅ "Escape Plan" is in final playlist
- ✅ Travis Scott tracks dominate (3-5 tracks)
- ✅ Similar artists (Future, Don Toliver)
- ✅ All tracks are trap/hip-hop
- ❌ No Indonesian pop, no Afrobeat, no slowed versions
```

#### Scenario 2: Single Artist Focus

```
Input: "Give me a Travis Scott playlist"
Expected:
- ✅ 80%+ Travis Scott tracks
- ✅ Diversity penalties relaxed
- ✅ Features/collaborations included
```

#### Scenario 3: Genre Exploration

```
Input: "French funk vibes"
Expected:
- ✅ Diverse French funk artists
- ✅ No trap, no Indonesian pop
- ✅ Diversity penalties enforced
```

### Unit Tests

- [ ] `test_intent_analyzer.py`
- [ ] `test_mood_analyzer_focused.py`
- [ ] `test_seed_gatherer.py`
- [ ] `test_user_anchor_strategy.py`
- [ ] `test_genre_filter.py`
- [ ] `test_artist_discovery_quality.py`

### Integration Tests

- [ ] `test_full_pipeline_explicit_track.py`
- [ ] `test_full_pipeline_artist_focus.py`
- [ ] `test_full_pipeline_genre_exploration.py`

---

## Success Metrics

### Phase 2 Completion Criteria

1. **User-Mentioned Track Inclusion**
   - ✅ 100% of explicitly mentioned tracks are in final playlist
   - ✅ Mentioned artists dominate the playlist (60%+ of tracks)

2. **Genre Consistency**
   - ✅ LLM quality score > 0.7
   - ✅ No off-genre outliers (Indonesian pop, wrong language)
   - ✅ <10% of tracks flagged as "feels out of place"

3. **Confidence Improvement**
   - ✅ Average confidence > 0.6 (up from 0.42)
   - ✅ <20% of tracks with confidence < 0.5

4. **Architectural Clarity**
   - ✅ Each agent has clear, single responsibility
   - ✅ Intent → Mood → Seeds → Recommendations pipeline
   - ✅ Quality gates prevent bad recommendations early

---

## Timeline Estimate

| Phase | Estimated Time | Priority |
|-------|----------------|----------|
| 2.1 - Intent Analyzer | 4-6 hours | 🔴 Critical |
| 2.2 - Refactor Mood Analyzer | 2-3 hours | 🔴 Critical |
| 2.3 - Seed Gatherer | 4-5 hours | 🔴 Critical |
| 2.4 - User Anchor Strategy | 3-4 hours | 🟡 High |
| 2.5 - Genre Filter | 3-4 hours | 🟡 High |
| 2.6 - Artist Discovery Quality | 2-3 hours | 🟡 High |
| 2.7 - Smarter Diversity | 2-3 hours | 🟢 Medium |
| 2.8 - Update Orchestrator | 2-3 hours | 🔴 Critical |
| 2.9 - Validation Logging | 2-3 hours | 🟢 Medium |

**Total Estimated Time**: 24-34 hours

---

## Notes

- **Phase 1 Progress**: User-mentioned track metadata is now correctly propagated, but tracks are still not being found/included
- **Root Cause**: The problem is earlier in the pipeline (anchor selection, search) AND in the recommendation sources (too much reliance on artist discovery)
- **Key Insight**: We need BOTH better search/selection AND a new recommendation strategy that prioritizes user mentions

---

## Questions to Resolve

1. Should we keep RecoBeat as a source, or rely more on Spotify recommendations?
2. What's the ideal ratio for User Anchor Strategy vs other sources?
3. Should genre filtering be strict (reject) or soft (penalize)?
4. How do we handle when user mentions an artist but not specific tracks?
