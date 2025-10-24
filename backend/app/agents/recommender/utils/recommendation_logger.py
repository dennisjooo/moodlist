"""Comprehensive logging for recommendation decisions and quality validation.

This module implements Phase 2.9: Validation Logging, providing detailed
tracking of why tracks are accepted, rejected, or filtered at each stage
of the recommendation pipeline.
"""

import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class RecommendationLogger:
    """Logger for tracking recommendation decisions throughout the pipeline.
    
    Tracks:
    - Track evaluation (acceptance/rejection)
    - Genre and feature matching
    - Diversity penalties
    - Filter decisions
    - Quality assessment
    """

    def __init__(self, session_id: str, workflow_id: Optional[str] = None):
        """Initialize the recommendation logger.

        Args:
            session_id: Current workflow session ID
            workflow_id: Optional workflow identifier for grouping
        """
        self.session_id = session_id
        self.workflow_id = workflow_id
        self.logger = logger.bind(
            session_id=session_id,
            workflow_id=workflow_id,
            component="recommendation_logger"
        )

    def log_track_evaluation(
        self,
        track_name: str,
        artist: str,
        track_id: Optional[str] = None,
        source: Optional[str] = None,
        confidence: Optional[float] = None,
        genre_match_score: Optional[float] = None,
        feature_match_score: Optional[float] = None,
        decision: str = "EVALUATED",
        rejection_reason: Optional[str] = None,
        **extra_context
    ):
        """Log evaluation of a candidate track.

        Args:
            track_name: Name of the track
            artist: Artist name
            track_id: Track ID (if available)
            source: Source of recommendation (e.g., 'artist_discovery', 'seed_based')
            confidence: Confidence score (0-1)
            genre_match_score: How well track matches target genre (0-1)
            feature_match_score: How well audio features match target (0-1)
            decision: Decision made (ACCEPTED, REJECTED, FILTERED, etc.)
            rejection_reason: Reason for rejection if applicable
            **extra_context: Additional context to log
        """
        log_data = {
            "event": "track_evaluation",
            "track_name": track_name,
            "artist": artist,
            "decision": decision,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if track_id:
            log_data["track_id"] = track_id
        if source:
            log_data["source"] = source
        if confidence is not None:
            log_data["confidence"] = round(confidence, 3)
        if genre_match_score is not None:
            log_data["genre_match_score"] = round(genre_match_score, 3)
        if feature_match_score is not None:
            log_data["feature_match_score"] = round(feature_match_score, 3)
        if rejection_reason:
            log_data["rejection_reason"] = rejection_reason

        # Add any extra context
        log_data.update(extra_context)

        # Log at appropriate level based on decision
        if decision == "REJECTED":
            self.logger.info("Track rejected", **log_data)
        elif decision == "ACCEPTED":
            self.logger.info("Track accepted", **log_data)
        else:
            self.logger.debug("Track evaluated", **log_data)

    def log_genre_filter_decision(
        self,
        track_name: str,
        artist: str,
        primary_genre: str,
        artist_genres: List[str],
        acousticness: Optional[float] = None,
        passed: bool = True,
        reason: Optional[str] = None
    ):
        """Log genre consistency filter decision.

        Args:
            track_name: Name of the track
            artist: Artist name
            primary_genre: Expected primary genre
            artist_genres: Artist's actual genres
            acousticness: Track acousticness value
            passed: Whether track passed the filter
            reason: Reason for failure if applicable
        """
        self.logger.info(
            "Genre filter decision",
            event="genre_filter",
            track_name=track_name,
            artist=artist,
            primary_genre=primary_genre,
            artist_genres=artist_genres,
            acousticness=acousticness,
            passed=passed,
            rejection_reason=reason if not passed else None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_diversity_penalty(
        self,
        track_name: str,
        artist: str,
        original_confidence: float,
        adjusted_confidence: float,
        penalty: float,
        artist_count: int,
        is_protected: bool = False
    ):
        """Log diversity penalty application.

        Args:
            track_name: Name of the track
            artist: Artist name
            original_confidence: Original confidence score
            adjusted_confidence: Confidence after penalty
            penalty: Penalty amount applied
            artist_count: Number of times artist appears
            is_protected: Whether track is protected from penalties
        """
        self.logger.debug(
            "Diversity penalty applied" if not is_protected else "Diversity penalty EXEMPT",
            event="diversity_penalty",
            track_name=track_name,
            artist=artist,
            original_confidence=round(original_confidence, 3),
            adjusted_confidence=round(adjusted_confidence, 3),
            penalty=round(penalty, 3),
            artist_count=artist_count,
            is_protected=is_protected,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_strategy_generation(
        self,
        strategy_name: str,
        target_count: int,
        generated_count: int,
        filtered_count: Optional[int] = None,
        **strategy_context
    ):
        """Log recommendation generation from a strategy.

        Args:
            strategy_name: Name of the strategy (e.g., 'user_anchor', 'artist_discovery')
            target_count: Target number of recommendations
            generated_count: Number of recommendations generated
            filtered_count: Number filtered out (if applicable)
            **strategy_context: Additional strategy-specific context
        """
        self.logger.info(
            f"Strategy generation: {strategy_name}",
            event="strategy_generation",
            strategy=strategy_name,
            target_count=target_count,
            generated_count=generated_count,
            filtered_count=filtered_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **strategy_context
        )

    def log_artist_discovery(
        self,
        artist_name: str,
        artist_id: str,
        tracks_fetched: int,
        tracks_accepted: int,
        avg_confidence: Optional[float] = None,
        rejection_reasons: Optional[List[str]] = None
    ):
        """Log artist discovery results.

        Args:
            artist_name: Name of the artist
            artist_id: Artist ID
            tracks_fetched: Number of tracks fetched from artist
            tracks_accepted: Number of tracks accepted
            avg_confidence: Average confidence of accepted tracks
            rejection_reasons: List of rejection reasons for filtered tracks
        """
        self.logger.info(
            f"Artist discovery: {artist_name}",
            event="artist_discovery",
            artist_name=artist_name,
            artist_id=artist_id,
            tracks_fetched=tracks_fetched,
            tracks_accepted=tracks_accepted,
            acceptance_rate=round(tracks_accepted / max(tracks_fetched, 1), 2),
            avg_confidence=round(avg_confidence, 3) if avg_confidence else None,
            rejection_reasons=rejection_reasons,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_quality_evaluation(
        self,
        overall_score: float,
        cohesion_score: float,
        confidence_score: float,
        diversity_score: float,
        meets_threshold: bool,
        issues: List[str],
        outlier_count: int = 0
    ):
        """Log quality evaluation results.

        Args:
            overall_score: Overall quality score (0-1)
            cohesion_score: Feature cohesion score
            confidence_score: Average confidence score
            diversity_score: Artist diversity score
            meets_threshold: Whether playlist meets quality threshold
            issues: List of quality issues
            outlier_count: Number of outlier tracks detected
        """
        self.logger.info(
            "Quality evaluation complete",
            event="quality_evaluation",
            overall_score=round(overall_score, 3),
            cohesion_score=round(cohesion_score, 3),
            confidence_score=round(confidence_score, 3),
            diversity_score=round(diversity_score, 3),
            meets_threshold=meets_threshold,
            issues=issues,
            outlier_count=outlier_count,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_llm_assessment(
        self,
        quality_score: float,
        issues: List[str],
        specific_concerns: List[str],
        genre_consistency: Optional[str] = None,
        outlier_tracks: Optional[List[str]] = None
    ):
        """Log LLM quality assessment results.

        Args:
            quality_score: LLM-assigned quality score (0-1)
            issues: General quality issues identified
            specific_concerns: Specific track concerns
            genre_consistency: Genre consistency assessment
            outlier_tracks: Tracks identified as outliers
        """
        self.logger.info(
            "LLM quality assessment",
            event="llm_assessment",
            quality_score=round(quality_score, 3),
            issues=issues,
            specific_concerns=specific_concerns[:5] if specific_concerns else [],  # Limit to 5 for brevity
            genre_consistency=genre_consistency,
            outlier_tracks=outlier_tracks[:5] if outlier_tracks else [],  # Limit to 5
            total_concerns=len(specific_concerns) if specific_concerns else 0,
            total_outliers=len(outlier_tracks) if outlier_tracks else 0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_user_anchor_priority(
        self,
        track_name: str,
        artist: str,
        is_user_mentioned: bool,
        is_protected: bool,
        confidence_boost: Optional[float] = None
    ):
        """Log user anchor prioritization.

        Args:
            track_name: Name of the track
            artist: Artist name
            is_user_mentioned: Whether user explicitly mentioned this track
            is_protected: Whether track is protected from filtering
            confidence_boost: Confidence boost applied (if any)
        """
        self.logger.info(
            f"User anchor: {track_name}",
            event="user_anchor_priority",
            track_name=track_name,
            artist=artist,
            is_user_mentioned=is_user_mentioned,
            is_protected=is_protected,
            confidence_boost=round(confidence_boost, 3) if confidence_boost else None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_seed_gathering(
        self,
        user_mentioned_tracks: List[str],
        anchor_tracks: List[str],
        discovered_artists: List[str],
        seed_pool_size: int
    ):
        """Log seed gathering results.

        Args:
            user_mentioned_tracks: Tracks explicitly mentioned by user
            anchor_tracks: Anchor tracks selected
            discovered_artists: Artists discovered
            seed_pool_size: Size of final seed pool
        """
        self.logger.info(
            "Seed gathering complete",
            event="seed_gathering",
            user_mentioned_count=len(user_mentioned_tracks),
            user_mentioned_tracks=user_mentioned_tracks[:5],  # Limit to 5
            anchor_track_count=len(anchor_tracks),
            anchor_tracks=anchor_tracks[:5],
            discovered_artist_count=len(discovered_artists),
            discovered_artists=discovered_artists[:10],  # Limit to 10
            seed_pool_size=seed_pool_size,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_filter_statistics(
        self,
        total_candidates: int,
        accepted: int,
        rejected_by_genre: int = 0,
        rejected_by_features: int = 0,
        rejected_by_language: int = 0,
        rejected_by_confidence: int = 0,
        rejected_other: int = 0
    ):
        """Log filtering statistics.

        Args:
            total_candidates: Total number of candidate tracks
            accepted: Number of tracks accepted
            rejected_by_genre: Number rejected due to genre mismatch
            rejected_by_features: Number rejected due to feature mismatch
            rejected_by_language: Number rejected due to language/region
            rejected_by_confidence: Number rejected due to low confidence
            rejected_other: Number rejected for other reasons
        """
        total_rejected = (
            rejected_by_genre + rejected_by_features + 
            rejected_by_language + rejected_by_confidence + rejected_other
        )
        
        self.logger.info(
            "Filtering statistics",
            event="filter_statistics",
            total_candidates=total_candidates,
            accepted=accepted,
            rejected=total_rejected,
            acceptance_rate=round(accepted / max(total_candidates, 1), 2),
            rejection_breakdown={
                "genre_mismatch": rejected_by_genre,
                "feature_mismatch": rejected_by_features,
                "language_region": rejected_by_language,
                "low_confidence": rejected_by_confidence,
                "other": rejected_other
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_recommendation_source_mix(
        self,
        user_anchor_count: int = 0,
        artist_discovery_count: int = 0,
        seed_based_count: int = 0,
        fallback_count: int = 0,
        total_count: int = 0
    ):
        """Log the mix of recommendation sources.

        Args:
            user_anchor_count: Tracks from user anchor strategy
            artist_discovery_count: Tracks from artist discovery
            seed_based_count: Tracks from seed-based recommendations
            fallback_count: Tracks from fallback sources
            total_count: Total number of recommendations
        """
        if total_count == 0:
            return

        self.logger.info(
            "Recommendation source mix",
            event="source_mix",
            total_recommendations=total_count,
            sources={
                "user_anchor": {
                    "count": user_anchor_count,
                    "percentage": round((user_anchor_count / total_count) * 100, 1)
                },
                "artist_discovery": {
                    "count": artist_discovery_count,
                    "percentage": round((artist_discovery_count / total_count) * 100, 1)
                },
                "seed_based": {
                    "count": seed_based_count,
                    "percentage": round((seed_based_count / total_count) * 100, 1)
                },
                "fallback": {
                    "count": fallback_count,
                    "percentage": round((fallback_count / total_count) * 100, 1)
                }
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_intent_analysis(
        self,
        intent_type: str,
        primary_genre: Optional[str] = None,
        genre_strictness: Optional[float] = None,
        user_mentioned_tracks: Optional[List[str]] = None,
        user_mentioned_artists: Optional[List[str]] = None,
        language_preferences: Optional[List[str]] = None,
        exclude_regions: Optional[List[str]] = None
    ):
        """Log intent analysis results (for Phase 2.1 compatibility).

        Args:
            intent_type: Type of intent (artist_focus, genre_exploration, mood_variety)
            primary_genre: Primary genre identified
            genre_strictness: How strict genre filtering should be (0-1)
            user_mentioned_tracks: Tracks explicitly mentioned
            user_mentioned_artists: Artists explicitly mentioned
            language_preferences: Preferred languages
            exclude_regions: Regions to exclude
        """
        self.logger.info(
            f"Intent analysis: {intent_type}",
            event="intent_analysis",
            intent_type=intent_type,
            primary_genre=primary_genre,
            genre_strictness=round(genre_strictness, 2) if genre_strictness else None,
            user_mentioned_tracks=user_mentioned_tracks[:5] if user_mentioned_tracks else [],
            user_mentioned_artists=user_mentioned_artists[:10] if user_mentioned_artists else [],
            language_preferences=language_preferences,
            exclude_regions=exclude_regions,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_pipeline_summary(
        self,
        phase: str,
        duration_seconds: float,
        input_count: int,
        output_count: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log pipeline phase summary.

        Args:
            phase: Pipeline phase name
            duration_seconds: Phase duration in seconds
            input_count: Number of items input to phase
            output_count: Number of items output from phase
            success: Whether phase completed successfully
            error_message: Error message if failed
        """
        log_level = "info" if success else "error"
        
        log_data = {
            "event": "pipeline_phase",
            "phase": phase,
            "duration_seconds": round(duration_seconds, 2),
            "input_count": input_count,
            "output_count": output_count,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if error_message:
            log_data["error_message"] = error_message

        if log_level == "error":
            self.logger.error(f"Pipeline phase failed: {phase}", **log_data)
        else:
            self.logger.info(f"Pipeline phase complete: {phase}", **log_data)


def create_recommendation_logger(
    session_id: str,
    workflow_id: Optional[str] = None
) -> RecommendationLogger:
    """Factory function to create a recommendation logger.

    Args:
        session_id: Current workflow session ID
        workflow_id: Optional workflow identifier

    Returns:
        Configured RecommendationLogger instance
    """
    return RecommendationLogger(session_id=session_id, workflow_id=workflow_id)
