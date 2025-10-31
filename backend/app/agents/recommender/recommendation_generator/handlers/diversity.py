"""Diversity management for recommendation lists."""

import structlog
from typing import List, Dict

from ....states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class DiversityManager:
    """Manages diversity in recommendation lists to avoid repetition."""

    def _ensure_diversity(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Ensure diversity in recommendations to avoid repetition.
        
        EXEMPTIONS: User-mentioned and protected tracks are NOT penalized.

        Args:
            recommendations: List of recommendations to diversify

        Returns:
            Diversified recommendations
        """
        if not recommendations:
            return recommendations

        # Count artist occurrences across ALL tracks first
        artist_counts = self._count_artist_occurrences(recommendations)

        # Apply diversity penalties
        diversified_recommendations, protected_count, penalized_count = self._apply_diversity_penalties(
            recommendations, artist_counts
        )

        # Sort with protected tracks first
        diversified_recommendations = self._sort_with_protected_priority(diversified_recommendations)

        logger.info(
            f"Diversity applied: {protected_count} tracks exempted (protected/user-mentioned), "
            f"{penalized_count} tracks penalized"
        )

        return diversified_recommendations

    def _count_artist_occurrences(
        self,
        recommendations: List[TrackRecommendation]
    ) -> Dict[str, int]:
        """Count how many times each artist appears in recommendations.

        Args:
            recommendations: List of recommendations

        Returns:
            Dictionary mapping artist names to occurrence counts
        """
        artist_counts = {}
        for rec in recommendations:
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1
        return artist_counts

    def _is_protected_track(self, rec: TrackRecommendation) -> bool:
        """Check if a track is protected from diversity penalties.

        Args:
            rec: Track recommendation to check

        Returns:
            True if track is protected
        """
        return rec.user_mentioned or rec.user_mentioned_artist or rec.protected

    def _calculate_diversity_penalty(
        self,
        rec: TrackRecommendation,
        artist_counts: Dict[str, int]
    ) -> float:
        """Calculate diversity penalty for a track based on artist repetition.

        Args:
            rec: Track recommendation
            artist_counts: Dictionary of artist occurrence counts

        Returns:
            Diversity penalty value
        """
        diversity_penalty = 0
        for artist in rec.artists:
            if artist_counts[artist] > 1:
                diversity_penalty += 0.1 * (artist_counts[artist] - 1)
        return diversity_penalty

    def _create_diversified_recommendation(
        self,
        rec: TrackRecommendation,
        adjusted_confidence: float
    ) -> TrackRecommendation:
        """Create a new recommendation with adjusted confidence score.

        Args:
            rec: Original recommendation
            adjusted_confidence: New confidence score

        Returns:
            New TrackRecommendation with adjusted confidence
        """
        return TrackRecommendation(
            track_id=rec.track_id,
            track_name=rec.track_name,
            artists=rec.artists,
            spotify_uri=rec.spotify_uri,
            confidence_score=adjusted_confidence,
            audio_features=rec.audio_features,
            reasoning=rec.reasoning,
            source=rec.source,
            user_mentioned=rec.user_mentioned,
            user_mentioned_artist=rec.user_mentioned_artist,
            anchor_type=rec.anchor_type,
            protected=rec.protected
        )

    def _apply_diversity_penalties(
        self,
        recommendations: List[TrackRecommendation],
        artist_counts: Dict[str, int]
    ) -> tuple[List[TrackRecommendation], int, int]:
        """Apply diversity penalties to non-protected tracks.

        Args:
            recommendations: List of recommendations
            artist_counts: Dictionary of artist occurrence counts

        Returns:
            Tuple of (diversified recommendations, protected count, penalized count)
        """
        diversified_recommendations = []
        protected_count = 0
        penalized_count = 0

        for rec in recommendations:
            if self._is_protected_track(rec):
                # Protected tracks keep original confidence score
                diversified_rec = self._create_diversified_recommendation(
                    rec, rec.confidence_score
                )
                diversified_recommendations.append(diversified_rec)
                protected_count += 1
                logger.debug(
                    f"Diversity: EXEMPT '{rec.track_name}' "
                    f"(user_mentioned={rec.user_mentioned}, user_mentioned_artist={rec.user_mentioned_artist}, protected={rec.protected})"
                )
            else:
                # Apply diversity penalty to non-protected tracks
                diversity_penalty = self._calculate_diversity_penalty(rec, artist_counts)
                adjusted_confidence = rec.confidence_score - diversity_penalty
                adjusted_confidence = max(adjusted_confidence, 0.1)  # Minimum confidence

                diversified_rec = self._create_diversified_recommendation(
                    rec, adjusted_confidence
                )
                diversified_recommendations.append(diversified_rec)
                
                if diversity_penalty > 0:
                    penalized_count += 1

        return diversified_recommendations, protected_count, penalized_count

    def _sort_with_protected_priority(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Sort recommendations with protected tracks first.

        Args:
            recommendations: List of recommendations to sort

        Returns:
            Sorted recommendations with protected tracks first
        """
        # Separate protected and non-protected tracks
        protected_tracks = [
            r for r in recommendations 
            if self._is_protected_track(r)
        ]
        non_protected_tracks = [
            r for r in recommendations 
            if not self._is_protected_track(r)
        ]
        
        # Sort each group independently by confidence score
        protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)
        non_protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Recombine with protected tracks first
        return protected_tracks + non_protected_tracks
