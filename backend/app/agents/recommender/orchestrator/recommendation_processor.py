"""Recommendation processor for handling duplicate removal and ratio enforcement."""

import structlog
from typing import List, Dict

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class RecommendationProcessor:
    """Processes recommendations by removing duplicates and enforcing source ratios."""

    def __init__(self):
        """Initialize the recommendation processor."""
        pass

    def remove_duplicates(self, recommendations: List[TrackRecommendation]) -> List[TrackRecommendation]:
        """Remove duplicate tracks from recommendations.

        Args:
            recommendations: List of track recommendations

        Returns:
            List with duplicates removed, preserving order and keeping first occurrence
        """
        seen_track_ids = set()
        seen_spotify_uris = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec.track_id not in seen_track_ids and rec.spotify_uri not in seen_spotify_uris:
                seen_track_ids.add(rec.track_id)
                seen_spotify_uris.add(rec.spotify_uri)
                unique_recommendations.append(rec)
            else:
                logger.debug(f"Removing duplicate: {rec.track_name} by {', '.join(rec.artists)}")
        
        if len(unique_recommendations) < len(recommendations):
            logger.info(f"Removed {len(recommendations) - len(unique_recommendations)} duplicate tracks")
        
        return unique_recommendations

    def enforce_source_ratio(
        self,
        recommendations: List[TrackRecommendation],
        max_count: int = 30,
        artist_ratio: float = 0.95
    ) -> List[TrackRecommendation]:
        """Enforce source ratio between artist discovery and RecoBeat recommendations.

        Args:
            recommendations: List of track recommendations
            max_count: Maximum number of recommendations to return
            artist_ratio: Ratio of artist recommendations (default 0.95 for 95% artist)

        Returns:
            List with enforced source ratio, sorted by confidence
        """
        recommendations = self.remove_duplicates(recommendations)
        source_groups = self.separate_by_source(recommendations)
        source_limits = self.calculate_source_limits(max_count, artist_ratio)
        capped_sources = self.cap_and_sort_by_source(source_groups, source_limits)
        return self.combine_and_sort_final(capped_sources, len(recommendations))

    def separate_by_source(self, recommendations: List[TrackRecommendation]) -> Dict[str, List[TrackRecommendation]]:
        """Separate recommendations by source."""
        grouped: Dict[str, List[TrackRecommendation]] = {
            "anchor_track": [],
            "artist_discovery": [],
            "reccobeat": [],
        }
        for recommendation in recommendations:
            if recommendation.source in grouped:
                grouped[recommendation.source].append(recommendation)
        return grouped

    def calculate_source_limits(self, max_count: int, artist_ratio: float) -> Dict[str, int]:
        """Calculate maximum counts for each source.
        
        Note: This returns a generic limit for anchor tracks, but the actual capping
        logic in cap_and_sort_by_source handles user-mentioned tracks specially
        (they don't count toward the limit).
        """
        max_anchor = 5  # Base limit for non-user-mentioned anchor tracks
        remaining = max_count - max_anchor
        max_artist = int(remaining * 0.98)  # 98% of remaining (increased from 95%)
        max_reccobeat = max(1, remaining - max_artist)  # Minimal fallback

        return {
            "anchor_track": max_anchor,
            "artist_discovery": max_artist,
            "reccobeat": max_reccobeat
        }

    def cap_and_sort_by_source(
        self,
        source_groups: Dict[str, List[TrackRecommendation]],
        source_limits: Dict[str, int]
    ) -> Dict[str, List[TrackRecommendation]]:
        """Cap each source to its limit and sort by confidence.
        
        User-mentioned anchor tracks don't count toward the anchor limit.
        """
        capped_sources = {}

        for source, recommendations in source_groups.items():
            limit = source_limits.get(source, 0)
            
            if source == "anchor_track":
                user_mentioned = [r for r in recommendations if r.user_mentioned]
                other_anchors = [r for r in recommendations if not r.user_mentioned]
                
                user_mentioned.sort(key=lambda r: r.confidence_score, reverse=True)
                other_anchors.sort(key=lambda r: r.confidence_score, reverse=True)
                
                capped_sources[source] = user_mentioned + other_anchors[:limit]
                
                logger.info(
                    f"Anchor track capping: {len(user_mentioned)} user-mentioned (unlimited), "
                    f"{len(other_anchors[:limit])} other anchors (capped at {limit})"
                )
            else:
                sorted_recs = sorted(recommendations, key=lambda r: r.confidence_score, reverse=True)
                capped_sources[source] = sorted_recs[:limit]

        return capped_sources

    def combine_and_sort_final(
        self,
        capped_sources: Dict[str, List[TrackRecommendation]],
        original_count: int
    ) -> List[TrackRecommendation]:
        """Combine sources and sort final list.
        
        CRITICAL: Anchor tracks (especially user-mentioned) must stay at the top.
        We maintain priority by combining in order without re-sorting.
        """
        # Get sources (already sorted by confidence within each group)
        anchor_recs = capped_sources.get("anchor_track", [])
        artist_recs = capped_sources.get("artist_discovery", [])
        reccobeat_recs = capped_sources.get("reccobeat", [])
        
        # Combine with anchors first (NEVER re-sort after this!)
        final_recs = anchor_recs + artist_recs + reccobeat_recs

        # Log results
        anchor_count = len(anchor_recs)
        artist_count = len(artist_recs)
        reccobeat_count = len(reccobeat_recs)
        artist_ratio = artist_count / (artist_count + reccobeat_count) if (artist_count + reccobeat_count) > 0 else 0

        logger.info(
            f"Final enforcement: {anchor_count} anchor + {artist_count} artist + {reccobeat_count} RecoBeat "
            f"= {len(final_recs)} total (was {original_count}, "
            f"artist:reccobeat ratio {artist_ratio*100:.0f}:{(1-artist_ratio)*100:.0f})"
        )

        return final_recs