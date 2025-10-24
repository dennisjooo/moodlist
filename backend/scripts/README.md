# Backend Scripts

Utility scripts for the MoodList backend.

## Log Analysis

### analyze_recommendation_logs.py

Comprehensive log analysis tool for recommendation pipeline logs. Analyzes structured JSON logs from the recommendation system to provide insights into decision-making processes.

**Usage**:

```bash
# Basic analysis
python scripts/analyze_recommendation_logs.py logs/agentic_system_*.log

# Filter by session
python scripts/analyze_recommendation_logs.py --session-id <session_id> logs/*.log

# Filter by event type
python scripts/analyze_recommendation_logs.py --event track_evaluation logs/*.log

# Export as JSON
python scripts/analyze_recommendation_logs.py --json logs/*.log > analysis.json
```

**Analysis Features**:

1. **Track Evaluation Analysis**
   - Acceptance/rejection rates
   - Top rejection reasons
   - Confidence scores by recommendation source
   - Min/max/avg confidence ranges

2. **Quality Evaluation Analysis**
   - Overall quality scores
   - Cohesion, confidence, diversity scores
   - Threshold pass rates
   - Common quality issues

3. **Source Mix Analysis**
   - Distribution of recommendations across sources
   - User anchor vs artist discovery vs seed-based
   - Percentage breakdowns over time

4. **Diversity Penalty Analysis**
   - Protection rates (user-mentioned/protected tracks)
   - Average penalty amounts
   - Penalized vs exempt tracks

5. **Genre Filter Analysis**
   - Pass/fail rates
   - Failure reasons breakdown
   - Genre consistency metrics

**Output Formats**:

- **Human-readable**: Formatted summary with sections for each analysis type
- **JSON**: Machine-readable output for integration with other tools

**Example**:

```bash
# Analyze yesterday's logs
python scripts/analyze_recommendation_logs.py logs/agentic_system_20241024_*.log

# Get JSON output for a specific session
python scripts/analyze_recommendation_logs.py \
  --session-id 62475038-94db-4e8e-ae22-c6ea7a2d0108 \
  --json logs/*.log
```

**Related Documentation**:

- [Phase 2 Logs Implementation Guide](../../docs/backend/phase-2-logs-implementation.md)
- [Phase 2 Executive Summary](../../docs/backend/phase-2-executive-summary.md)
- [Phase 2 Recommendation Quality Overhaul](../../docs/backend/phase-2-recommendation-quality-overhaul.md)

## Future Scripts

Planned utility scripts:

- Database migration helpers
- Data export/import tools
- Performance benchmarking scripts
- Cache warming utilities
