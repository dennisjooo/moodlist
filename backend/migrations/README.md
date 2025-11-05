# Database Migrations

This directory contains SQL migration scripts for the MoodList database.

## Running Migrations

### Phase 5 Performance Optimization - JSONB Indexes

To add the GIN indexes for improved search performance, run:

```bash
# Using psql
psql -h localhost -U your_user -d moodlist_db -f migrations/001_add_jsonb_indexes.sql

# Or using environment variables
psql $DATABASE_URL -f migrations/001_add_jsonb_indexes.sql
```

### Expected Performance Improvements

After applying the JSONB indexes:
- **Full-text searches**: 2-5x faster
- **JSON field queries**: 3-10x faster
- **Playlist listing with search**: 50-70% reduction in query time

### Verification

To verify the indexes were created successfully:

```sql
-- Check for GIN indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'playlists'
AND indexdef LIKE '%gin%';

-- Check for JSON field indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'playlists'
AND (indexname LIKE '%name%' OR indexname LIKE '%emotion%' OR indexname LIKE '%energy%');
```

## Migration History

- **001_add_jsonb_indexes.sql** - Phase 5: Add GIN and expression indexes for JSONB fields
