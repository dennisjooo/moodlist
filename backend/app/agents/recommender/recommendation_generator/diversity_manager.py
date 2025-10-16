"""Diversity management for recommendation lists."""

import logging
from typing import List

from ...states.agent_state import TrackRecommendation
from ..utils import TrackRecommendationFactory

logger = logging.getLogger(__name__)


class DiversityManager:
    """Manages diversity in recommendation lists to avoid repetition."""

    def _ensure_diversity(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Ensure diversity in recommendations to avoid repetition.

        Args:
            recommendations: List of recommendations to diversify

        Returns:
            Diversified recommendations
        """
        if not recommendations:
            return recommendations

        # Simple diversity approach: reduce weight of artists that appear multiple times
        artist_counts = {}
        diversified_recommendations = []

        for rec in recommendations:
            # Count artist occurrences
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

            # Reduce confidence score for artists that appear multiple times
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
                reasoning=rec.reasoning,  # Keep original reasoning, adjustment is in confidence score
                source=rec.source
            )

            diversified_recommendations.append(diversified_rec)

        # Re-sort by adjusted confidence
        diversified_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

        return diversified_recommendations
