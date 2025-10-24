# Phase 2.9: Validation Logging - Implementation Guide

## Status: ✅ IMPLEMENTED

**Location**: `backend/app/agents/recommender/utils/recommendation_logger.py`

## Overview

The `RecommendationLogger` provides comprehensive, structured logging for tracking recommendation decisions throughout the pipeline. It helps understand why tracks are accepted, rejected, or filtered at each stage.

## Key Features

1. **Track Evaluation Logging** - Track acceptance/rejection with scores and reasons
2. **Genre Filter Logging** - Log genre consistency filter decisions
3. **Diversity Penalty Logging** - Track diversity penalty applications
4. **Strategy Generation Logging** - Log outputs from each recommendation strategy
5. **Artist Discovery Logging** - Track artist discovery results and filtering
6. **Quality Evaluation Logging** - Log quality assessment results
7. **LLM Assessment Logging** - Track LLM quality evaluations
8. **Pipeline Phase Logging** - Summary logging for pipeline phases
9. **Source Mix Logging** - Track distribution of recommendation sources
10. **Intent Analysis Logging** - Log intent analysis results (Phase 2.1 ready)

## Usage Examples

### Basic Setup

```python
from app.agents.recommender.utils.recommendation_logger import create_recommendation_logger

# Create logger for a workflow session
rec_logger = create_recommendation_logger(
    session_id=state.session_id,
    workflow_id=state.metadata.get("workflow_id")
)
```

### Track Evaluation

```python
# Log track acceptance
rec_logger.log_track_evaluation(
    track_name="Escape Plan",
    artist="Travis Scott",
    track_id="6BQfYRja8VqvC3PNsZdVSE",
    source="user_anchor_strategy",
    confidence=0.95,
    genre_match_score=0.92,
    feature_match_score=0.88,
    decision="ACCEPTED",
    energy=0.85,
    valence=0.45
)

# Log track rejection
rec_logger.log_track_evaluation(
    track_name="Seandainya",
    artist="Vierra",
    track_id="xyz123",
    source="artist_discovery",
    confidence=0.45,
    genre_match_score=0.12,
    feature_match_score=0.35,
    decision="REJECTED",
    rejection_reason="language_mismatch_indonesian"
)
```

### Genre Filter Decisions

```python
rec_logger.log_genre_filter_decision(
    track_name="Seandainya",
    artist="Vierra",
    primary_genre="trap",
    artist_genres=["indonesian pop", "pop"],
    acousticness=0.65,
    passed=False,
    reason="Artist genres don't match trap; acousticness too high (0.65 > 0.3)"
)
```

### Diversity Penalties

```python
# Log diversity penalty for repeated artist
rec_logger.log_diversity_penalty(
    track_name="SICKO MODE",
    artist="Travis Scott",
    original_confidence=0.88,
    adjusted_confidence=0.78,
    penalty=0.10,
    artist_count=3,
    is_protected=False
)

# Log exemption for user-mentioned tracks
rec_logger.log_diversity_penalty(
    track_name="Escape Plan",
    artist="Travis Scott",
    original_confidence=0.95,
    adjusted_confidence=0.95,
    penalty=0.0,
    artist_count=4,
    is_protected=True
)
```

### Strategy Generation

```python
rec_logger.log_strategy_generation(
    strategy_name="user_anchor_strategy",
    target_count=8,
    generated_count=12,
    filtered_count=3,
    user_mentioned_seeds=["Escape Plan", "SICKO MODE"],
    spotify_api_calls=3
)
```

### Artist Discovery

```python
rec_logger.log_artist_discovery(
    artist_name="Travis Scott",
    artist_id="0Y5tJX1MQlXJYWs9hjnNp8",
    tracks_fetched=10,
    tracks_accepted=7,
    avg_confidence=0.82,
    rejection_reasons=[
        "Feature mismatch: too acoustic",
        "Low confidence: 0.42",
        "Already in playlist"
    ]
)
```

### Quality Evaluation

```python
rec_logger.log_quality_evaluation(
    overall_score=0.78,
    cohesion_score=0.82,
    confidence_score=0.71,
    diversity_score=0.85,
    meets_threshold=True,
    issues=[
        "2 tracks below 0.5 confidence",
        "Minor genre variance in 3 tracks"
    ],
    outlier_count=2
)
```

### LLM Assessment

```python
rec_logger.log_llm_assessment(
    quality_score=0.85,
    issues=[
        "High quality trap playlist",
        "Strong genre consistency"
    ],
    specific_concerns=[
        "Track 'One Dance' feels slightly off-genre",
        "Consider more aggressive trap tracks"
    ],
    genre_consistency="excellent",
    outlier_tracks=["One Dance by Drake"]
)
```

### User Anchor Priority

```python
rec_logger.log_user_anchor_priority(
    track_name="Escape Plan",
    artist="Travis Scott",
    is_user_mentioned=True,
    is_protected=True,
    confidence_boost=0.15
)
```

### Seed Gathering

```python
rec_logger.log_seed_gathering(
    user_mentioned_tracks=["Escape Plan", "SICKO MODE"],
    anchor_tracks=["goosebumps", "STARGAZING"],
    discovered_artists=["Travis Scott", "Future", "Don Toliver"],
    seed_pool_size=8
)
```

### Filter Statistics

```python
rec_logger.log_filter_statistics(
    total_candidates=85,
    accepted=62,
    rejected_by_genre=8,
    rejected_by_features=5,
    rejected_by_language=4,
    rejected_by_confidence=6,
    rejected_other=0
)
```

### Recommendation Source Mix

```python
rec_logger.log_recommendation_source_mix(
    user_anchor_count=8,
    artist_discovery_count=8,
    seed_based_count=3,
    fallback_count=1,
    total_count=20
)
```

### Intent Analysis (Phase 2.1 Ready)

```python
rec_logger.log_intent_analysis(
    intent_type="artist_focus",
    primary_genre="trap",
    genre_strictness=0.9,
    user_mentioned_tracks=["Escape Plan"],
    user_mentioned_artists=["Travis Scott", "SZA"],
    language_preferences=["english"],
    exclude_regions=["southeast_asian", "indonesian"]
)
```

### Pipeline Phase Summary

```python
rec_logger.log_pipeline_summary(
    phase="recommendation_generation",
    duration_seconds=4.23,
    input_count=30,
    output_count=20,
    success=True
)
```

## Integration with Existing Components

### In Recommendation Engine

```python
class RecommendationEngine:
    def __init__(self, reccobeat_service, spotify_service):
        # ... existing init ...
        self.rec_logger = None  # Will be set per-workflow
    
    async def generate_recommendations(self, state: AgentState):
        # Create logger for this workflow
        self.rec_logger = create_recommendation_logger(
            session_id=state.session_id,
            workflow_id=state.metadata.get("workflow_id")
        )
        
        # Log strategy generation
        self.rec_logger.log_strategy_generation(
            strategy_name="artist_discovery",
            target_count=target,
            generated_count=len(recommendations)
        )
        
        # Log each track evaluation
        for track in candidate_tracks:
            self.rec_logger.log_track_evaluation(
                track_name=track.name,
                artist=track.artist,
                confidence=track.confidence,
                decision="ACCEPTED" if track.passes_filter else "REJECTED",
                rejection_reason=track.rejection_reason
            )
```

### In Diversity Manager

```python
class DiversityManager:
    def _ensure_diversity(self, recommendations):
        rec_logger = create_recommendation_logger(session_id=self.session_id)
        
        for rec in recommendations:
            if rec.user_mentioned or rec.protected:
                rec_logger.log_diversity_penalty(
                    track_name=rec.track_name,
                    artist=rec.artists[0],
                    original_confidence=rec.confidence_score,
                    adjusted_confidence=rec.confidence_score,
                    penalty=0.0,
                    artist_count=artist_counts[rec.artists[0]],
                    is_protected=True
                )
            else:
                penalty = calculate_penalty(rec)
                rec_logger.log_diversity_penalty(
                    track_name=rec.track_name,
                    artist=rec.artists[0],
                    original_confidence=rec.confidence_score,
                    adjusted_confidence=rec.confidence_score - penalty,
                    penalty=penalty,
                    artist_count=artist_counts[rec.artists[0]],
                    is_protected=False
                )
```

### In Quality Evaluator

```python
class QualityEvaluator:
    async def evaluate_playlist_quality(self, state):
        rec_logger = create_recommendation_logger(session_id=state.session_id)
        
        # ... evaluation logic ...
        
        rec_logger.log_quality_evaluation(
            overall_score=evaluation["overall_score"],
            cohesion_score=evaluation["cohesion_score"],
            confidence_score=evaluation["confidence_score"],
            diversity_score=evaluation["diversity_score"],
            meets_threshold=evaluation["meets_threshold"],
            issues=evaluation["issues"],
            outlier_count=len(evaluation["outlier_tracks"])
        )
        
        if evaluation.get("llm_assessment"):
            rec_logger.log_llm_assessment(
                quality_score=evaluation["llm_assessment"]["quality_score"],
                issues=evaluation["llm_assessment"]["issues"],
                specific_concerns=evaluation["llm_assessment"]["specific_concerns"],
                genre_consistency=evaluation["llm_assessment"].get("genre_consistency"),
                outlier_tracks=evaluation["llm_assessment"].get("outlier_tracks")
            )
```

## Log Output Examples

### Structured JSON Logs (with structlog)

```json
{
  "event": "track_evaluation",
  "session_id": "62475038-94db-4e8e-ae22-c6ea7a2d0108",
  "workflow_id": "workflow_001",
  "component": "recommendation_logger",
  "track_name": "Escape Plan",
  "artist": "Travis Scott",
  "track_id": "6BQfYRja8VqvC3PNsZdVSE",
  "source": "user_anchor_strategy",
  "confidence": 0.95,
  "genre_match_score": 0.92,
  "feature_match_score": 0.88,
  "decision": "ACCEPTED",
  "timestamp": "2024-01-15T14:23:45.123456Z"
}
```

```json
{
  "event": "track_evaluation",
  "session_id": "62475038-94db-4e8e-ae22-c6ea7a2d0108",
  "workflow_id": "workflow_001",
  "component": "recommendation_logger",
  "track_name": "Seandainya",
  "artist": "Vierra",
  "track_id": "xyz123",
  "source": "artist_discovery",
  "confidence": 0.45,
  "genre_match_score": 0.12,
  "feature_match_score": 0.35,
  "decision": "REJECTED",
  "rejection_reason": "language_mismatch_indonesian",
  "timestamp": "2024-01-15T14:23:47.234567Z"
}
```

## Benefits

1. **Debugging** - Easy to trace why tracks are included/excluded
2. **Quality Analysis** - Understand quality evaluation decisions
3. **Performance Tracking** - Monitor strategy effectiveness
4. **Troubleshooting** - Identify issues in the recommendation pipeline
5. **Metrics** - Generate reports on acceptance/rejection rates
6. **Audit Trail** - Complete history of recommendation decisions

## Log Analysis

### Querying Logs

Use `jq` to analyze JSON logs:

```bash
# Find all rejected tracks
cat logs/agentic_system_*.log | jq 'select(.event == "track_evaluation" and .decision == "REJECTED")'

# Count rejection reasons
cat logs/agentic_system_*.log | jq -r 'select(.event == "track_evaluation" and .decision == "REJECTED") | .rejection_reason' | sort | uniq -c

# Get average confidence by source
cat logs/agentic_system_*.log | jq 'select(.event == "track_evaluation" and .decision == "ACCEPTED") | {source, confidence}' | jq -s 'group_by(.source) | map({source: .[0].source, avg_confidence: (map(.confidence) | add / length)})'

# Find outlier tracks
cat logs/agentic_system_*.log | jq 'select(.event == "llm_assessment") | .outlier_tracks'
```

### Python Log Analysis Script

A comprehensive log analysis script is provided at `backend/scripts/analyze_recommendation_logs.py`.

**Usage**:

```bash
# Analyze all logs in directory
python backend/scripts/analyze_recommendation_logs.py logs/agentic_system_*.log

# Analyze logs for specific session
python backend/scripts/analyze_recommendation_logs.py --session-id abc123 logs/*.log

# Analyze only track evaluation events
python backend/scripts/analyze_recommendation_logs.py --event track_evaluation logs/*.log

# Export to JSON for further processing
python backend/scripts/analyze_recommendation_logs.py --json logs/*.log > analysis.json
```

**Features**:

1. **Track Evaluation Analysis** - Acceptance/rejection rates, rejection reasons, confidence by source
2. **Quality Evaluation Analysis** - Average scores, threshold pass rates, common issues
3. **Source Mix Analysis** - Distribution of recommendations across sources
4. **Diversity Penalty Analysis** - Protection rates, average penalties
5. **Genre Filter Analysis** - Pass rates, failure reasons

**Example Output**:

```
================================================================================
RECOMMENDATION PIPELINE LOG ANALYSIS
================================================================================

Total Logs: 1,247
Sessions: 15
Workflows: 15

Event Distribution:
  track_evaluation: 450
  quality_evaluation: 15
  diversity_penalty: 380
  source_mix: 15
  genre_filter: 120

================================================================================
TRACK EVALUATION ANALYSIS
================================================================================

Total Evaluated: 450
Acceptance Rate: 72.4%
Rejection Rate: 27.6%

Top Rejection Reasons:
  language_mismatch_indonesian: 42
  feature_mismatch_too_acoustic: 28
  low_confidence: 24
  genre_mismatch: 18

Source Statistics:
  user_anchor_strategy:
    Count: 95
    Avg Confidence: 0.847
    Range: 0.650 - 0.980
  artist_discovery:
    Count: 198
    Avg Confidence: 0.723
    Range: 0.420 - 0.910
  seed_based:
    Count: 33
    Avg Confidence: 0.681
    Range: 0.510 - 0.820
```

## Future Enhancements

1. **Recommendation Dashboard** - Real-time visualization of recommendation decisions
2. **A/B Testing** - Track effectiveness of different strategies
3. **User Feedback Integration** - Correlate logs with user satisfaction
4. **Automated Alerts** - Notify when quality thresholds are consistently missed
5. **Log Aggregation** - Centralized logging service for multi-worker setups

## Related Documentation

- [Phase 2 Executive Summary](./phase-2-executive-summary.md)
- [Phase 2 Recommendation Quality Overhaul](./phase-2-recommendation-quality-overhaul.md)
- [Anchor Track Flow Analysis](./anchor-track-flow-analysis.md)

## Next Steps

To fully implement Phase 2.9 across the codebase:

1. ✅ Create `RecommendationLogger` class
2. ✅ Create comprehensive log analysis script
3. ✅ Add to utils module exports
4. ✅ Document usage patterns and integration examples
5. ⏳ Integrate into `RecommendationEngine`
6. ⏳ Integrate into `DiversityManager`
7. ⏳ Integrate into `QualityEvaluator`
8. ⏳ Integrate into recommendation strategies
9. ⏳ Integrate into filter components (when Phase 2.5 is implemented)
10. ⏳ Add to monitoring/observability tools
11. ⏳ Set up log aggregation pipeline (CloudWatch/Datadog)
12. ⏳ Create dashboards for real-time monitoring
