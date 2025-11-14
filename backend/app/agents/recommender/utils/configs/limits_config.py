"""Limits and batch processing settings for the recommender system."""

from dataclasses import dataclass


@dataclass
class LimitsConfig:
    """Configuration for batch processing, candidate gathering, and discovery limits."""

    # Batch processing settings
    track_energy_analysis_batch_size: int = 8  # Playlist ordering agent
    track_energy_analysis_timeout_seconds: int = 45  # Max wait per LLM batch
    seed_chunk_size: int = 3  # Seed-based recommendation generation
    artist_batch_validation_size: int = 30  # LLM batch artist validation

    # Candidate gathering limits
    genre_anchor_search_limit: int = 5  # How many genres to fan out when gathering anchors
    artist_recommendation_limit: int = 10  # How many LLM-suggested artists to enrich
    anchor_track_limit: int = 5  # Default number of anchor tracks to keep after scoring
    user_track_extraction_limit: int = 5  # Max number of track mentions to try resolving
    user_track_search_results_limit: int = 5  # How many Spotify results to inspect per mentioned track
    artist_anchor_processing_limit: int = 5  # Max artists to process for anchor building per request
    mentioned_artist_track_limit: int = 5  # Top tracks kept for user-mentioned artists
    default_artist_track_limit: int = 3  # Top tracks kept for non-mentioned artists
    artist_search_limit: int = 3  # Number of Spotify artist search results to inspect per query
    artist_top_tracks_max_concurrency: int = 4  # Parallel calls when hydrating artist top tracks

    # Artist discovery controls
    fallback_search_keyword_limit: int = 5  # How many fallback search keywords to try
    fallback_artist_search_limit: int = 12  # Spotify limit when probing fallback keywords
    llm_batch_validation_trigger: int = 10  # Min artist count before running batch LLM filtering
    llm_minimum_filtered_artists: int = 5  # Minimum acceptable LLM output before falling back
    artist_discovery_result_limit: int = 20  # Final number of artists to keep for downstream steps
    genre_artist_search_limit: int = 20  # Artists to fetch per-genre via direct search
    genre_track_search_limit: int = 15  # Track-based artist discoveries per genre
    heuristic_pruning_min_artists: int = 15  # Skip pruning when artist pool is already small
    heuristic_min_artist_popularity: int = 15  # Minimum popularity before we discard an artist
    heuristic_pruned_artist_limit: int = 30  # Cap heuristically-pruned list before LLM work
