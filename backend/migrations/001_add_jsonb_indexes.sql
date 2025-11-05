-- Migration: Add GIN indexes for JSONB fields to improve search performance
-- Phase 5 Performance Optimization
-- Run this migration to add indexes to existing database

-- Create GIN index on playlist_data for full-text search on playlist name
CREATE INDEX IF NOT EXISTS ix_playlist_data_gin
ON playlists USING GIN (playlist_data);

-- Create GIN index on mood_analysis_data for search on emotions and energy levels
CREATE INDEX IF NOT EXISTS ix_mood_analysis_data_gin
ON playlists USING GIN (mood_analysis_data);

-- Create GIN index on recommendations_data for search on track recommendations
CREATE INDEX IF NOT EXISTS ix_recommendations_data_gin
ON playlists USING GIN (recommendations_data);

-- Create specific indexes for frequently accessed JSON fields
-- Index for playlist name searches (common in UI)
CREATE INDEX IF NOT EXISTS ix_playlist_data_name
ON playlists ((playlist_data->>'name'));

-- Index for primary emotion searches
CREATE INDEX IF NOT EXISTS ix_mood_analysis_primary_emotion
ON playlists ((mood_analysis_data->>'primary_emotion'));

-- Index for energy level searches
CREATE INDEX IF NOT EXISTS ix_mood_analysis_energy_level
ON playlists ((mood_analysis_data->>'energy_level'));

-- Add comment to track migration
COMMENT ON INDEX ix_playlist_data_gin IS 'Phase 5: GIN index for full-text search on playlist metadata';
COMMENT ON INDEX ix_mood_analysis_data_gin IS 'Phase 5: GIN index for mood analysis searches';
COMMENT ON INDEX ix_recommendations_data_gin IS 'Phase 5: GIN index for recommendation searches';
