"""Centralized configuration for the recommender package.

This module provides a unified configuration interface that combines all sub-configs.
Individual config modules are organized in the configs/ subdirectory.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from .configs import (
    AudioFeaturesConfig,
    LimitsConfig,
    MoodConfig,
    OrchestrationConfig,
    TextProcessingConfig,
)


@dataclass
class RecommenderConfig:
    """Centralized configuration for the recommender system.

    This class aggregates all configuration modules into a single interface,
    providing backward compatibility with the original flat config structure.
    """

    # Sub-configuration modules
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    audio_features: AudioFeaturesConfig = field(default_factory=AudioFeaturesConfig)
    mood: MoodConfig = field(default_factory=MoodConfig)
    text_processing: TextProcessingConfig = field(default_factory=TextProcessingConfig)

    # Backward compatibility properties - orchestration
    @property
    def max_iterations(self) -> int:
        return self.orchestration.max_iterations

    @property
    def cohesion_threshold(self) -> float:
        return self.orchestration.cohesion_threshold

    @property
    def quality_threshold(self) -> float:
        return self.orchestration.quality_threshold

    @property
    def timeout_per_agent(self) -> int:
        return self.orchestration.timeout_per_agent

    @property
    def max_retries(self) -> int:
        return self.orchestration.max_retries

    @property
    def max_recommendations(self) -> int:
        return self.orchestration.max_recommendations

    @property
    def diversity_factor(self) -> float:
        return self.orchestration.diversity_factor

    @property
    def artist_recommendation_ratio(self) -> float:
        return self.orchestration.artist_recommendation_ratio

    @property
    def min_playlist_count(self) -> int:
        return self.orchestration.min_playlist_count

    @property
    def max_playlist_count(self) -> int:
        return self.orchestration.max_playlist_count

    @property
    def max_tracks_per_artist(self) -> int:
        return self.orchestration.max_tracks_per_artist

    @property
    def user_mentioned_artist_ratio(self) -> float:
        return self.orchestration.user_mentioned_artist_ratio

    # Backward compatibility properties - limits (batch processing)
    @property
    def track_energy_analysis_batch_size(self) -> int:
        return self.limits.track_energy_analysis_batch_size

    @property
    def track_energy_analysis_timeout_seconds(self) -> int:
        return self.limits.track_energy_analysis_timeout_seconds

    @property
    def seed_chunk_size(self) -> int:
        return self.limits.seed_chunk_size

    @property
    def artist_batch_validation_size(self) -> int:
        return self.limits.artist_batch_validation_size

    # Backward compatibility properties - limits (candidate gathering)
    @property
    def genre_anchor_search_limit(self) -> int:
        return self.limits.genre_anchor_search_limit

    @property
    def artist_recommendation_limit(self) -> int:
        return self.limits.artist_recommendation_limit

    @property
    def anchor_track_limit(self) -> int:
        return self.limits.anchor_track_limit

    @property
    def user_track_extraction_limit(self) -> int:
        return self.limits.user_track_extraction_limit

    @property
    def user_track_search_results_limit(self) -> int:
        return self.limits.user_track_search_results_limit

    @property
    def artist_anchor_processing_limit(self) -> int:
        return self.limits.artist_anchor_processing_limit

    @property
    def mentioned_artist_track_limit(self) -> int:
        return self.limits.mentioned_artist_track_limit

    @property
    def default_artist_track_limit(self) -> int:
        return self.limits.default_artist_track_limit

    @property
    def artist_search_limit(self) -> int:
        return self.limits.artist_search_limit

    @property
    def artist_top_tracks_max_concurrency(self) -> int:
        return self.limits.artist_top_tracks_max_concurrency

    # Backward compatibility properties - limits (artist discovery)
    @property
    def fallback_search_keyword_limit(self) -> int:
        return self.limits.fallback_search_keyword_limit

    @property
    def fallback_artist_search_limit(self) -> int:
        return self.limits.fallback_artist_search_limit

    @property
    def llm_batch_validation_trigger(self) -> int:
        return self.limits.llm_batch_validation_trigger

    @property
    def llm_minimum_filtered_artists(self) -> int:
        return self.limits.llm_minimum_filtered_artists

    @property
    def artist_discovery_result_limit(self) -> int:
        return self.limits.artist_discovery_result_limit

    @property
    def genre_artist_search_limit(self) -> int:
        return self.limits.genre_artist_search_limit

    @property
    def genre_track_search_limit(self) -> int:
        return self.limits.genre_track_search_limit

    @property
    def heuristic_pruning_min_artists(self) -> int:
        return self.limits.heuristic_pruning_min_artists

    @property
    def heuristic_min_artist_popularity(self) -> int:
        return self.limits.heuristic_min_artist_popularity

    @property
    def heuristic_pruned_artist_limit(self) -> int:
        return self.limits.heuristic_pruned_artist_limit

    # Backward compatibility properties - audio features
    @property
    def default_feature_weights(self) -> Dict[str, float]:
        return self.audio_features.default_feature_weights

    @property
    def feature_tolerances(self) -> Dict[str, float]:
        return self.audio_features.feature_tolerances

    @property
    def critical_features(self) -> List[str]:
        return self.audio_features.critical_features

    # Backward compatibility properties - mood
    @property
    def mood_synonyms(self) -> Dict[str, List[str]]:
        return self.mood.mood_synonyms

    @property
    def mood_profiles(self) -> Dict[str, Dict[str, Any]]:
        return self.mood.mood_profiles

    @property
    def keyword_feature_mappings(self) -> List[Dict[str, Any]]:
        return self.mood.keyword_feature_mappings

    # Backward compatibility properties - text processing
    @property
    def stop_words(self) -> Set[str]:
        return self.text_processing.stop_words

    @property
    def known_genres(self) -> Set[str]:
        return self.text_processing.known_genres

    @property
    def language_indicators(self) -> Dict[str, List[Any]]:
        return self.text_processing.language_indicators


# Global configuration instance
config = RecommenderConfig()
