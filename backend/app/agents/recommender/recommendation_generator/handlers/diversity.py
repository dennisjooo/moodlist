"""Diversity management for recommendation lists."""

from collections import defaultdict
from typing import Dict, List, Optional

import structlog

from ....states.agent_state import TrackRecommendation
from ...utils import config as recommender_config

logger = structlog.get_logger(__name__)


class DiversityManager:
    """Manages diversity in recommendation lists to avoid repetition."""

    def __init__(
        self,
        max_tracks_per_artist: Optional[int] = None,
        user_mentioned_artist_ratio: Optional[float] = None
    ):
        """Configure diversity manager.

        Args:
            max_tracks_per_artist: Hard cap for how many tracks from a single artist
                can appear in the final list. User-mentioned/protected tracks always remain,
                but they still count toward the cap for subsequent items.
            user_mentioned_artist_ratio: Fraction of the playlist target that user-mentioned
                artists are allowed to occupy (shared across all mentioned artists).
        """
        if max_tracks_per_artist is None:
            max_tracks_per_artist = recommender_config.max_tracks_per_artist
        if user_mentioned_artist_ratio is None:
            user_mentioned_artist_ratio = recommender_config.user_mentioned_artist_ratio

        self.max_tracks_per_artist = max_tracks_per_artist
        self.user_mentioned_artist_ratio = max(0.0, min(1.0, user_mentioned_artist_ratio))

    def _ensure_diversity(
        self,
        recommendations: List[TrackRecommendation],
        target_count: Optional[int] = None
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

        # Apply hard artist limits (default: 2 tracks per artist)
        diversified_recommendations = self._enforce_artist_limits(
            diversified_recommendations,
            target_count=target_count
        )

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

    def _is_penalty_exempt(self, rec: TrackRecommendation) -> bool:
        """Check if a track is protected from diversity penalties."""
        return rec.user_mentioned or rec.protected

    def _is_cap_exempt(self, rec: TrackRecommendation) -> bool:
        """Check if a track should bypass artist caps entirely."""
        return rec.user_mentioned

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
            if self._is_penalty_exempt(rec):
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
            if self._is_penalty_exempt(r)
        ]
        non_protected_tracks = [
            r for r in recommendations
            if not self._is_penalty_exempt(r)
        ]

        # Sort each group independently by confidence score
        protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)
        non_protected_tracks.sort(key=lambda x: x.confidence_score, reverse=True)

        # Recombine with protected tracks first
        return protected_tracks + non_protected_tracks

    def _enforce_artist_limits(
        self,
        recommendations: List[TrackRecommendation],
        target_count: Optional[int] = None
    ) -> List[TrackRecommendation]:
        """Ensure no artist exceeds the configured track limit."""
        if not recommendations or self.max_tracks_per_artist <= 0:
            return recommendations

        target_total = max(target_count or len(recommendations) or 1, 1)
        user_artist_total_limit = max(
            self.max_tracks_per_artist,
            int(target_total * self.user_mentioned_artist_ratio)
        )

        artist_usage: Dict[str, int] = defaultdict(int)
        user_artist_total = 0
        limited_recommendations: List[TrackRecommendation] = []
        dropped_count = 0

        for rec in recommendations:
            is_user_artist = bool(rec.user_mentioned_artist)

            if self._is_cap_exempt(rec):
                limited_recommendations.append(rec)
                logger.debug(
                    "artist_limit_bypass_user_track",
                    track_name=rec.track_name,
                    artists=rec.artists
                )
                continue

            if not self._can_include_track(
                rec,
                artist_usage,
                is_user_artist,
                user_artist_total,
                user_artist_total_limit
            ):
                dropped_count += 1
                logger.debug(
                    "artist_limit_skipped",
                    track_name=rec.track_name,
                    artists=rec.artists,
                    limit=self.max_tracks_per_artist,
                    user_artist_limit=user_artist_total_limit,
                    reason="artist_cap_exceeded"
                )
                continue

            limited_recommendations.append(rec)
            self._increment_artist_usage(artist_usage, rec)
            if is_user_artist:
                user_artist_total += 1

        if dropped_count:
            logger.info(
                "artist_limit_enforced",
                dropped=dropped_count,
                artist_cap=self.max_tracks_per_artist,
                user_artist_cap=user_artist_total_limit
            )

        return limited_recommendations

    def _can_include_track(
        self,
        rec: TrackRecommendation,
        artist_usage: Dict[str, int],
        is_user_artist: bool,
        user_artist_total: int,
        user_artist_total_limit: int
    ) -> bool:
        """Check if adding this track would violate artist usage limits."""
        if is_user_artist and user_artist_total >= user_artist_total_limit:
            return False

        for artist in rec.artists:
            if artist_usage[artist] >= self.max_tracks_per_artist:
                return False
        return True

    def _increment_artist_usage(
        self,
        artist_usage: Dict[str, int],
        rec: TrackRecommendation
    ) -> None:
        """Increment usage counters for all artists on the track."""
        for artist in rec.artists:
            artist_usage[artist] += 1

    def enforce_popularity_tiers(
        self,
        recommendations: List[TrackRecommendation],
        target_count: int
    ) -> List[TrackRecommendation]:
        """Enforce popularity tier balancing to ensure mix of mainstream, mid-tier, and niche tracks.

        Args:
            recommendations: List of track recommendations
            target_count: Target number of tracks for final playlist

        Returns:
            Balanced list of recommendations
        """
        if not recommendations or target_count <= 0:
            return recommendations

        limits = recommender_config.limits
        mainstream_threshold = limits.popularity_tier_mainstream_threshold
        mid_threshold = limits.popularity_tier_mid_threshold
        mainstream_ratio = limits.popularity_tier_mainstream_ratio
        mid_ratio = limits.popularity_tier_mid_ratio
        niche_ratio = limits.popularity_tier_niche_ratio

        # Clamp target count to available recommendations
        target_count = min(target_count, len(recommendations))

        # Calculate tier targets
        mainstream_target = int(target_count * mainstream_ratio)
        mid_target = int(target_count * mid_ratio)
        niche_target = int(target_count * niche_ratio)

        # Group recommendations by popularity tier
        mainstream = []
        mid_tier = []
        niche = []

        for rec in recommendations:
            # Get popularity from audio_features or default to 50
            popularity = 50  # Default
            if rec.audio_features and isinstance(rec.audio_features, dict):
                popularity = rec.audio_features.get("popularity", 50)

            if popularity > mainstream_threshold:
                mainstream.append(rec)
            elif popularity >= mid_threshold:
                mid_tier.append(rec)
            else:
                niche.append(rec)

        # Sort each tier by confidence score
        mainstream.sort(key=lambda r: r.confidence_score, reverse=True)
        mid_tier.sort(key=lambda r: r.confidence_score, reverse=True)
        niche.sort(key=lambda r: r.confidence_score, reverse=True)

        # Build balanced list
        balanced = []

        # Take from each tier according to ratios (with flexibility)
        selected_mainstream = mainstream[:mainstream_target]
        selected_mid = mid_tier[:mid_target]
        selected_niche = niche[:niche_target]

        balanced.extend(selected_mainstream)
        balanced.extend(selected_mid)
        balanced.extend(selected_niche)

        # Fill remaining slots with overflow from any tier (highest confidence first)
        if len(balanced) < target_count:
            overflow = (
                mainstream[mainstream_target:] +
                mid_tier[mid_target:] +
                niche[niche_target:]
            )
            overflow.sort(key=lambda r: r.confidence_score, reverse=True)
            balanced.extend(overflow[:target_count - len(balanced)])

        logger.info(
            f"Popularity tier balancing: {len(selected_mainstream)} mainstream, "
            f"{len(selected_mid)} mid-tier, {len(selected_niche)} niche "
            f"(target: {mainstream_target}/{mid_target}/{niche_target})"
        )

        return balanced[:target_count]
