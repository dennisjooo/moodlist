"""Orchestration and agent settings for the recommender system."""

from dataclasses import dataclass


@dataclass
class OrchestrationConfig:
    """Configuration for orchestration and agent behavior."""

    # Orchestration settings
    max_iterations: int = 1
    cohesion_threshold: float = 0.65
    quality_threshold: float = 0.75

    # Agent settings
    timeout_per_agent: int = 120
    max_retries: int = 3

    # Recommendation generation settings
    max_recommendations: int = 30
    diversity_factor: float = 0.7
    artist_recommendation_ratio: float = 0.95  # 95% artist, 5% RecoBeat
    min_playlist_count: int = 15
    max_playlist_count: int = 30
    max_tracks_per_artist: int = 2  # Hard cap for repeat artists (excluding protected)
    user_mentioned_artist_ratio: float = 0.5  # Max share of playlist for user-mentioned artists
