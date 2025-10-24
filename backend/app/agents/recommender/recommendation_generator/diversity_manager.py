"""Diversity management for recommendation lists."""

import structlog
from typing import List

from ...states.agent_state import TrackRecommendation

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
        artist_counts = {}
        for rec in recommendations:
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

        diversified_recommendations = []
        protected_count = 0
        penalized_count = 0

        for rec in recommendations:
            # CRITICAL: Skip diversity penalty for protected tracks
            if rec.user_mentioned or rec.protected:
                # Keep original confidence for user-mentioned/protected tracks
                diversified_rec = TrackRecommendation(
                    track_id=rec.track_id,
                    track_name=rec.track_name,
                    artists=rec.artists,
                    spotify_uri=rec.spotify_uri,
                    confidence_score=rec.confidence_score,  # NO PENALTY
                    audio_features=rec.audio_features,
                    reasoning=rec.reasoning,
                    source=rec.source,
                    user_mentioned=rec.user_mentioned,
                    anchor_type=rec.anchor_type,
                    protected=rec.protected
                )
                diversified_recommendations.append(diversified_rec)
                protected_count += 1
                logger.debug(
                    f"Diversity: EXEMPT '{rec.track_name}' "
                    f"(user_mentioned={rec.user_mentioned}, protected={rec.protected})"
                )
                continue

            # Apply diversity penalty to non-protected tracks
            diversity_penalty = 0
            for artist in rec.artists:
                if artist_counts[artist] > 1:
                    diversity_penalty += 0.1 * (artist_counts[artist] - 1)

            # Apply diversity penalty
            adjusted_confidence = rec.confidence_score - diversity_penalty
            adjusted_confidence = max(adjusted_confidence, 0.1)  # Minimum confidence

            # Create new recommendation with adjusted confidence
            diversified_rec = TrackRecommendation(
                track_id=rec.track_id,
                track_name=rec.track_name,
                artists=rec.artists,
                spotify_uri=rec.spotify_uri,
                confidence_score=adjusted_confidence,
                audio_features=rec.audio_features,
                reasoning=rec.reasoning,
                source=rec.source,
                user_mentioned=rec.user_mentioned,
                anchor_type=rec.anchor_type,
                protected=rec.protected
            )

            diversified_recommendations.append(diversified_rec)
            if diversity_penalty > 0:
                penalized_count += 1

        # CRITICAL: Separate protected and non-protected tracks before sorting
        # Protected tracks (user-mentioned) must maintain priority
        protected_tracks = [r for r in diversified_recommendations if r.protected or r.user_mentioned]
        non_protected_tracks = [r for r in diversified_recommendations if not (r.protected or r.user_mentioned)]
        
        # Sort each group independently
        protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)
        non_protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Recombine with protected tracks first
        diversified_recommendations = protected_tracks + non_protected_tracks

        logger.info(
            f"Diversity applied: {protected_count} tracks exempted (protected/user-mentioned), "
            f"{penalized_count} tracks penalized"
        )

        return diversified_recommendations
