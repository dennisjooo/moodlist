"""Recommendation processor for handling duplicate removal and ratio enforcement."""

import math
from collections import Counter, defaultdict
from itertools import chain
from typing import Dict, Iterable, List

import structlog

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
                logger.debug(
                    "duplicate_removed",
                    track_id=rec.track_id,
                    track_name=rec.track_name,
                    artists=rec.artists,
                )

        if len(unique_recommendations) < len(recommendations):
            logger.info(
                "duplicates_removed",
                removed=len(recommendations) - len(unique_recommendations),
                before=len(recommendations),
                after=len(unique_recommendations),
            )

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
        # Remove duplicates from the original list
        recommendations = self.remove_duplicates(recommendations)

        if not recommendations or max_count <= 0:
            return []
        
        # Separate recommendations by source
        source_groups = self.separate_by_source(recommendations)

        # Calculate limits for each source
        source_limits = self.calculate_source_limits(max_count, artist_ratio)

        # Cap and sort each source
        capped_sources, overflow_sources = self.cap_and_sort_by_source(source_groups, source_limits)

        # Combine and sort final list
        final_recommendations = self.combine_and_sort_final(
            capped_sources,
            len(recommendations),
            max_count,
        )

        # If we're still short of the desired count, top up from overflow pools
        final_recommendations = self.fill_with_overflow(
            final_recommendations,
            overflow_sources,
            max_count
        )

        return final_recommendations

    def separate_by_source(self, recommendations: List[TrackRecommendation]) -> Dict[str, List[TrackRecommendation]]:
        """Separate recommendations by source."""
        source_groups: Dict[str, List[TrackRecommendation]] = defaultdict(list)
        for recommendation in recommendations:
            source = recommendation.source or "unknown"
            source_groups[source].append(recommendation)

        # Ensure the expected keys are always present for downstream logic
        for expected in ("artist_discovery", "anchor_track", "reccobeat"):
            source_groups.setdefault(expected, [])

        return dict(source_groups)

    def calculate_source_limits(self, max_count: int, artist_ratio: float) -> Dict[str, int]:
        """Calculate maximum counts for each source.
        
        Note: This returns a generic limit for anchor tracks, but the actual capping
        logic in cap_and_sort_by_source handles user-mentioned tracks specially
        (they don't count toward the limit).
        """
        if max_count <= 0:
            return {
                "anchor_track": 0,
                "artist_discovery": 0,
                "reccobeat": 0,
            }

        max_anchor = min(5, max_count)  # Base limit for non-user-mentioned anchor tracks
        remaining = max(0, max_count - max_anchor)

        artist_ratio = max(0.0, min(1.0, artist_ratio))
        max_artist = math.floor(remaining * artist_ratio)
        max_artist = min(max_artist, remaining)
        max_reccobeat = max(0, remaining - max_artist)

        # Ensure we leave room for at least one RecoBeat fallback when possible
        if remaining > 0 and max_reccobeat == 0 and artist_ratio < 1:
            max_reccobeat = 1
            max_artist = max(0, remaining - 1)

        return {
            "anchor_track": max_anchor,
            "artist_discovery": max_artist,
            "reccobeat": max_reccobeat
        }

    def cap_and_sort_by_source(
        self,
        source_groups: Dict[str, List[TrackRecommendation]],
        source_limits: Dict[str, int]
    ) -> tuple[Dict[str, List[TrackRecommendation]], Dict[str, List[TrackRecommendation]]]:
        """Cap each source to its limit and sort by confidence.

        CRITICAL: User-mentioned anchor tracks don't count toward the anchor limit.
        """
        capped_sources: Dict[str, List[TrackRecommendation]] = {}
        overflow_sources: Dict[str, List[TrackRecommendation]] = {}

        for source, recommendations in source_groups.items():
            if not recommendations:
                capped_sources[source] = []
                overflow_sources[source] = []
                continue

            limit = source_limits.get(source, 0)

            # Special handling for anchor tracks: user-mentioned tracks are unlimited
            if source == "anchor_track":
                user_mentioned: List[TrackRecommendation] = []
                other_anchors: List[TrackRecommendation] = []
                for rec in recommendations:
                    (user_mentioned if rec.user_mentioned else other_anchors).append(rec)

                # Sort each group independently
                user_mentioned.sort(key=lambda r: r.confidence_score, reverse=True)
                other_anchors.sort(key=lambda r: r.confidence_score, reverse=True)

                # Cap other anchors, but keep all user-mentioned
                capped_sources[source] = user_mentioned + other_anchors[:limit]
                overflow_sources[source] = other_anchors[limit:]

                logger.info(
                    "anchor_track_capping",
                    user_mentioned=len(user_mentioned),
                    allowed=len(other_anchors[:limit]),
                    overflow=len(overflow_sources[source]),
                    limit=limit,
                )
            else:
                # Normal capping for other sources
                recommendations.sort(key=lambda r: r.confidence_score, reverse=True)

                if limit >= len(recommendations):
                    capped_sources[source] = recommendations
                    overflow_sources[source] = []
                else:
                    capped_sources[source] = recommendations[:limit]
                    overflow_sources[source] = recommendations[limit:]

                logger.info(
                    "source_capping",
                    source=source,
                    allowed=len(capped_sources[source]),
                    overflow=len(overflow_sources[source]),
                    limit=limit,
                )

        return capped_sources, overflow_sources

    def combine_and_sort_final(
        self,
        capped_sources: Dict[str, List[TrackRecommendation]],
        original_count: int,
        max_count: int,
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
        combined_recs = anchor_recs + artist_recs + reccobeat_recs

        if len(combined_recs) > max_count:
            trimmed = len(combined_recs) - max_count
            logger.info(
                "final_cap_applied",
                requested=max_count,
                current=len(combined_recs),
                trimmed=trimmed,
            )
            final_recs = combined_recs[:max_count]
        else:
            final_recs = combined_recs

        counts = Counter(
            recommendation.source for recommendation in final_recs
            if recommendation.source in {"anchor_track", "artist_discovery", "reccobeat"}
        )

        anchor_count = counts.get("anchor_track", 0)
        artist_count = counts.get("artist_discovery", 0)
        reccobeat_count = counts.get("reccobeat", 0)
        available = artist_count + reccobeat_count
        artist_ratio = artist_count / available if available else 0

        logger.info(
            "ratio_enforcement_complete",
            anchor_count=anchor_count,
            artist_count=artist_count,
            reccobeat_count=reccobeat_count,
            total=len(final_recs),
            original=original_count,
            artist_ratio=artist_ratio,
        )

        return final_recs

    def fill_with_overflow(
        self,
        recommendations: List[TrackRecommendation],
        overflow_sources: Dict[str, List[TrackRecommendation]],
        max_count: int
    ) -> List[TrackRecommendation]:
        """Top up recommendations if capping left us short of the target size.

        We prioritise overflow anchors first (since they're closest to the user's
        intent), then artist discovery tracks, and finally RecoBeat fallbacks.
        """
        if len(recommendations) >= max_count:
            return recommendations

        shortfall = max_count - len(recommendations)
        if shortfall <= 0:
            return recommendations

        logger.info("overflow_fill_start", shortfall=shortfall)

        # Preserve original list while allowing modifications
        final_recommendations = list(recommendations)

        # Maintain sets for fast duplicate checks
        seen_track_ids = {rec.track_id for rec in final_recommendations}
        seen_spotify_uris = {rec.spotify_uri for rec in final_recommendations if rec.spotify_uri}

        # Prioritise overflow order: anchors -> artist discovery -> RecoBeat
        overflow_priority: Iterable[TrackRecommendation] = chain(
            overflow_sources.get("anchor_track", []),
            overflow_sources.get("artist_discovery", []),
            overflow_sources.get("reccobeat", []),
        )

        added = 0
        for rec in overflow_priority:
            if added >= shortfall:
                break

            if rec.track_id in seen_track_ids:
                continue

            if rec.spotify_uri and rec.spotify_uri in seen_spotify_uris:
                continue

            final_recommendations.append(rec)
            seen_track_ids.add(rec.track_id)
            if rec.spotify_uri:
                seen_spotify_uris.add(rec.spotify_uri)
            added += 1

        if added:
            logger.info(
                "overflow_fill_complete",
                added=added,
                total=len(final_recommendations),
            )
        else:
            logger.info("overflow_fill_none_available")

        return final_recommendations
