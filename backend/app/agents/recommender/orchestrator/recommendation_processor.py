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
        # Separate recommendations by source
        source_groups = self.separate_by_source(recommendations)

        # Calculate limits for each source
        source_limits = self.calculate_source_limits(max_count, artist_ratio)

        # Cap and sort each source
        capped_sources = self.cap_and_sort_by_source(source_groups, source_limits)

        # Combine and sort final list
        final_recommendations = self.combine_and_sort_final(capped_sources, len(recommendations))

        return final_recommendations

    def separate_by_source(self, recommendations: List[TrackRecommendation]) -> Dict[str, List[TrackRecommendation]]:
        """Separate recommendations by source."""
        source_groups = {
            "artist_discovery": [r for r in recommendations if r.source == "artist_discovery"],
            "anchor_track": [r for r in recommendations if r.source == "anchor_track"],
            "reccobeat": [r for r in recommendations if r.source == "reccobeat"]
        }
        return source_groups

    def calculate_source_limits(self, max_count: int, artist_ratio: float) -> Dict[str, int]:
        """Calculate maximum counts for each source."""
        max_anchor = 5  # Always allow up to 5 anchor tracks
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
        """Cap each source to its limit and sort by confidence."""
        capped_sources = {}

        for source, recommendations in source_groups.items():
            limit = source_limits.get(source, 0)
            # Sort by confidence and cap
            sorted_recs = sorted(recommendations, key=lambda r: r.confidence_score, reverse=True)
            capped_sources[source] = sorted_recs[:limit]

        return capped_sources

    def combine_and_sort_final(
        self,
        capped_sources: Dict[str, List[TrackRecommendation]],
        original_count: int
    ) -> List[TrackRecommendation]:
        """Combine sources and sort final list."""
        # Combine all sources
        final_recs = []
        for source_recs in capped_sources.values():
            final_recs.extend(source_recs)

        # Sort final list by confidence
        final_recs.sort(key=lambda r: r.confidence_score, reverse=True)

        # Log results
        anchor_count = len(capped_sources.get("anchor_track", []))
        artist_count = len(capped_sources.get("artist_discovery", []))
        reccobeat_count = len(capped_sources.get("reccobeat", []))
        artist_ratio = artist_count / (artist_count + reccobeat_count) if (artist_count + reccobeat_count) > 0 else 0

        logger.info(
            f"Final enforcement: {anchor_count} anchor + {artist_count} artist + {reccobeat_count} RecoBeat "
            f"= {len(final_recs)} total (was {original_count}, "
            f"artist:reccobeat ratio {artist_ratio*100:.0f}:{(1-artist_ratio)*100:.0f})"
        )

        return final_recs