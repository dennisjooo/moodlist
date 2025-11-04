# Recommender System Architecture Summary

## High-Level Flow

```
User Prompt
    ↓
1. IntentAnalyzerAgent
   - Extracts: user_mentioned_tracks, user_mentioned_artists, exclude_regions
   - Determines: intent_type, language_preferences, quality_threshold
    ↓
2. MoodAnalyzerAgent
   - Analyzes mood → audio features (energy, valence, tempo, etc.)
   - Generates: artist_recommendations, genre_keywords
   - Infers: preferred_regions, excluded_regions
    ↓
3. OrchestratorAgent (Main coordinator)
   ├─ a. SeedGathererAgent
   │   ├─ Search user-mentioned tracks
   │   ├─ Select anchor tracks (via AnchorTrackSelector)
   │   │   └─ Uses LLM to score and filter anchors
   │   └─ Build seed pool from anchors + top tracks
   │
   ├─ b. RecommendationGeneratorAgent
   │   └─ RecommendationEngine coordinates 4 strategies:
   │       ├─ UserAnchorStrategy (40% if user mentions exist)
   │       ├─ ArtistDiscoveryStrategy (40% from discovered artists)
   │       ├─ SeedBasedGenerator (15% from seed_tracks)
   │       │   └─ Calls RecoBeat API with negative_seeds
   │       └─ Fallback (5% if needed)
   │   └─ TrackFilter validates relevance
   │   └─ DiversityManager ensures variety
   │
   ├─ c. QualityEvaluator
   │   ├─ CohesionCalculator (audio feature matching)
   │   └─ LLM assessment (cultural/genre fit)
   │
   └─ d. Iterative Improvement (up to 3 iterations)
       └─ ImprovementStrategy applies:
           ├─ filter_and_replace: Adds outliers to negative_seeds
           ├─ reseed_from_clean: Uses top tracks as new seeds
           ├─ adjust_feature_weights: Stricter matching
           └─ generate_more: More recommendations
    ↓
4. Final Processing
   - Enrich with Spotify URIs
   - Remove duplicates
   - Enforce source ratios
```

## Key Components

### State Management

- **AgentState**: Central state object passed between agents
  - `mood_prompt`: User's original request
  - `mood_analysis`: Audio features + genres + artists
  - `seed_tracks`: Track IDs used for seeding RecoBeat
  - `negative_seeds`: Track IDs to avoid
  - `recommendations`: Final playlist (TrackRecommendation objects)
  - `metadata`: Contains anchor_tracks, intent_analysis, etc.

### Anchor Tracks

- **Purpose**: High-quality genre-representative tracks
- **Sources**:
  1. User-mentioned tracks (highest priority)
  2. Artist top tracks (from LLM-recommended artists)
  3. Genre search results (scored by LLM)
- **Metadata**:
  - `user_mentioned`: True if explicitly mentioned by user
  - `anchor_type`: "user" | "artist_mentioned" | "genre"
  - `protected`: True if should never be filtered
  - `llm_score`: LLM confidence (0-1)

### Seed Tracks

- **Purpose**: Track IDs used to generate similar recommendations
- **Built from**: Anchor tracks + top user tracks
- **Used by**: SeedBasedGenerator → RecoBeat API

### Negative Seeds

- **Purpose**: Track IDs to explicitly avoid
- **Set by**:
  1. SeedSelector.get_negative_seeds() - Least popular tracks
  2. ImprovementStrategy._filter_and_replace() - Outliers from iterations
- **Passed to**: RecoBeat API as `negativeSeeds` parameter
- **⚠️ BUG**: Not checked by TrackFilter, so tracks still appear!

### Recommendation Strategies

#### 1. UserAnchorStrategy (40%)

- Generates from user-mentioned tracks/artists
- High priority, always included if user mentions exist

#### 2. ArtistDiscoveryStrategy (40%)

- Uses `mood_matched_artists` from ArtistDiscovery
- Gets top tracks from each discovered artist
- Scores by audio feature match

#### 3. SeedBasedGenerator (15%)

- Calls RecoBeat API with seed_tracks
- Passes negative_seeds to avoid similar tracks
- Returns RecoBeat recommendations

#### 4. Anchor Track Inclusion

- Adds anchor tracks directly to recommendations
- Marked with source="anchor_track"

### Quality Evaluation

#### CohesionCalculator

- Calculates feature match against target_features
- Identifies outliers (tracks with poor match)
- Returns cohesion_score (0-1)

#### QualityEvaluator (LLM)

- Evaluates cultural/genre fit
- Checks for specific concerns (e.g., language mismatch)
- Returns overall_score (0-1)

### Improvement Strategies

#### filter_and_replace

1. Identifies outliers from quality evaluation
2. Adds outlier IDs to `state.negative_seeds`
3. Keeps good tracks
4. Generates new recommendations to replace filtered tracks

#### reseed_from_clean

1. Sorts tracks by confidence + cohesion
2. Uses top 5 as new seeds
3. Adds bottom 3 to negative_seeds
4. Regenerates recommendations

#### adjust_feature_weights

- Increases `feature_weight` parameter (4.5 → 5.0)
- Makes RecoBeat matching stricter

#### generate_more

- Generates additional recommendations to reach target count

## Critical Bugs Identified

### 1. Negative Seeds Not Filtering

**Location**: `TrackFilter._filter_and_rank_recommendations()`
**Problem**: Never checks `state.negative_seeds`, so outliers reappear
**Fix**: Add negative_seeds parameter and filter early

### 2. Bad Anchors Become Seeds

**Location**: `SeedGathererAgent._build_seed_pool()` line 344
**Problem**: Adds ALL anchor IDs without checking llm_score or protected status
**Fix**: Only add anchors with `llm_score >= 0.6` OR `user_mentioned == True`

### 3. No Convergence Detection

**Location**: `OrchestratorAgent.perform_iterative_improvement()`
**Problem**: Always runs 3 iterations even if not improving
**Fix**: Check score improvement, stop if < 2% gain for 2 iterations

### 4. Excluded Regions Not Populated

**Location**: `IntentAnalyzerAgent` + `MoodAnalyzer`
**Problem**: LLM systems exist but not connecting exclude_regions properly
**Fix**: Ensure intent_analyzer sets exclude_regions, mood_analyzer uses them

## LLM Systems Already In Place

### IntentAnalyzerAgent

- ✅ Extracts user_mentioned_tracks, user_mentioned_artists
- ✅ Determines exclude_regions, language_preferences
- ⚠️ Not always populating exclude_regions

### MoodAnalyzer

- ✅ `_infer_regional_context()` already sets excluded_regions
- ✅ Used by TrackFilter for language penalties

### LLMServices (Anchor Selection)

- ✅ `filter_tracks_by_relevance()` - Filters culturally irrelevant
- ✅ `score_candidates()` - Assigns llm_score to anchors
- ✅ `finalize_selection()` - Prioritizes user-mentioned

### TrackFilter

- ✅ `validate_track_relevance()` - Checks artist match, language, genre
- ✅ `_apply_mood_filtering()` - Uses excluded_regions for filtering
- ⚠️ Missing negative_seeds check

## Files to Modify

1. `backend/app/agents/recommender/recommendation_generator/handlers/track_filter.py`
   - Add negative_seeds filtering

2. `backend/app/agents/recommender/seed_gatherer/seed_gatherer_agent.py`
   - Line 344: Add quality check before adding to seed_pool

3. `backend/app/agents/recommender/orchestrator/orchestrator_agent.py`
   - Add convergence detection to perform_iterative_improvement()

4. `backend/app/agents/recommender/intent_analyzer/intent_analyzer_agent.py`
   - Ensure exclude_regions is always populated

5. Update all strategy callers:
   - `SeedBasedGenerator.generate_recommendations()`
   - `ArtistDiscoveryStrategy.generate_recommendations()`
   - `UserAnchorStrategy.generate_recommendations()`
