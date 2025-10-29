"""Phase assignment logic for playlist ordering."""

import structlog
from typing import Any, Dict, List

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class PhaseAssigner:
    """Handles assignment of tracks to energy flow phases."""

    def __init__(self):
        """Initialize the phase assigner."""
        self.phase_order = ["opening", "build", "mid", "high", "descent", "closure"]
        self.phase_priority_order = ["opening", "closure", "high", "build", "descent", "mid"]

    def assign_tracks_to_phases(
        self,
        recommendations: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> Dict[str, List[TrackRecommendation]]:
        """Assign tracks to energy flow phases.

        Args:
            recommendations: List of recommendations
            analysis_map: Mapping of track_id to analysis
            strategy: Ordering strategy

        Returns:
            Dictionary mapping phase names to track lists
        """
        # Get target distribution
        adjusted_distribution = self._calculate_phase_distribution(
            strategy, len(recommendations)
        )

        # Score each track for each phase
        track_phase_scores = self._score_tracks_for_phases(
            recommendations, analysis_map
        )

        # Assign tracks to phases
        phase_buckets = self._assign_using_greedy_best_fit(
            track_phase_scores, adjusted_distribution
        )

        return phase_buckets

    def _calculate_phase_distribution(
        self,
        strategy: Dict[str, Any],
        track_count: int
    ) -> Dict[str, int]:
        """Calculate adjusted phase distribution based on actual track count.

        Args:
            strategy: Ordering strategy
            track_count: Number of tracks

        Returns:
            Adjusted phase distribution
        """
        phase_distribution = strategy.get("phase_distribution", {
            "opening": 2,
            "build": 5,
            "mid": 8,
            "high": 7,
            "descent": 4,
            "closure": 2
        })

        # Adjust distribution based on actual track count
        total_target = sum(phase_distribution.values())
        scale_factor = track_count / total_target if total_target > 0 else 1

        adjusted_distribution = {
            phase: max(1, round(count * scale_factor))
            for phase, count in phase_distribution.items()
        }

        # Ensure we use all tracks
        diff = track_count - sum(adjusted_distribution.values())
        if diff != 0:
            # Adjust the largest phase
            largest_phase = max(adjusted_distribution, key=adjusted_distribution.get)
            adjusted_distribution[largest_phase] += diff

        return adjusted_distribution

    def _score_tracks_for_phases(
        self,
        recommendations: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[tuple]:
        """Score each track for each phase.

        Args:
            recommendations: List of recommendations
            analysis_map: Track analyses

        Returns:
            List of (track, analysis, scores) tuples
        """
        from .phase_scorer import PhaseScorer
        scorer = PhaseScorer()

        track_phase_scores = []
        for rec in recommendations:
            analysis = analysis_map.get(rec.track_id, {})
            scores = scorer.calculate_phase_scores(rec, analysis)
            track_phase_scores.append((rec, analysis, scores))

        return track_phase_scores

    def _assign_using_greedy_best_fit(
        self,
        track_phase_scores: List[tuple],
        adjusted_distribution: Dict[str, int]
    ) -> Dict[str, List[TrackRecommendation]]:
        """Assign tracks to phases using greedy best-fit approach.

        Args:
            track_phase_scores: List of (track, analysis, scores) tuples
            adjusted_distribution: Target distribution

        Returns:
            Phase buckets
        """
        phase_buckets = {phase: [] for phase in adjusted_distribution.keys()}
        used_tracks = set()

        # Assign tracks with strong phase preferences
        for phase in self.phase_priority_order:
            if phase not in adjusted_distribution:
                continue

            target_count = adjusted_distribution[phase]

            # Get available tracks sorted by score for this phase
            available = [
                (rec, analysis, scores)
                for rec, analysis, scores in track_phase_scores
                if rec.track_id not in used_tracks
            ]
            available.sort(key=lambda x: x[2].get(phase, 0), reverse=True)

            # Assign top tracks to this phase
            for rec, analysis, scores in available[:target_count]:
                phase_buckets[phase].append(rec)
                used_tracks.add(rec.track_id)

                if len(phase_buckets[phase]) >= target_count:
                    break

        return phase_buckets

