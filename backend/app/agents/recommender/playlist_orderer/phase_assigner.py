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
        # Get phase distribution from strategy or use defaults
        phase_distribution = strategy.get("phase_distribution", {
            "opening": 2,
            "build": 5,
            "mid": 8,
            "high": 7,
            "descent": 4,
            "closure": 2
        })

        # Normalize to standard phases
        normalized_distribution = self._normalize_phase_names(phase_distribution)
        
        # Scale to match track count
        adjusted_distribution = self._scale_distribution(normalized_distribution, track_count)
        
        # Ensure exact track count
        adjusted_distribution = self._adjust_to_exact_count(adjusted_distribution, track_count)

        logger.info(f"Phase distribution for {track_count} tracks: {adjusted_distribution}")
        
        return adjusted_distribution

    def _normalize_phase_names(self, phase_distribution: Dict[str, int]) -> Dict[str, int]:
        """Normalize phase distribution to use only standard phase names.

        Args:
            phase_distribution: Raw phase distribution from strategy

        Returns:
            Normalized distribution with only standard phases
        """
        all_phases = ["opening", "build", "mid", "high", "descent", "closure"]
        normalized = {phase: 0 for phase in all_phases}
        
        # Separate valid and invalid phases
        invalid_phases = {k: v for k, v in phase_distribution.items() if k not in all_phases}
        
        if invalid_phases:
            logger.warning(
                f"LLM invented custom phase names: {list(invalid_phases.keys())}. "
                f"Redistributing to standard phases."
            )
            # Redistribute invalid phase tracks to 'mid' as fallback
            extra_tracks = sum(invalid_phases.values())
            if extra_tracks > 0:
                logger.info(f"Redistributing {extra_tracks} tracks from custom phases to 'mid'")
                normalized["mid"] = extra_tracks
        
        # Merge valid phases
        for phase, count in phase_distribution.items():
            if phase in all_phases:
                normalized[phase] = count
        
        return normalized

    def _scale_distribution(self, distribution: Dict[str, int], target_count: int) -> Dict[str, int]:
        """Scale phase distribution to match target track count.

        Args:
            distribution: Normalized phase distribution
            target_count: Target number of tracks

        Returns:
            Scaled distribution
        """
        total_target = sum(distribution.values())
        
        if total_target == 0:
            # No distribution specified - use equal distribution
            return self._create_equal_distribution(target_count)
        
        # Scale proportionally
        scale_factor = target_count / total_target
        scaled = {
            phase: max(0, round(count * scale_factor))
            for phase, count in distribution.items()
        }
        
        return scaled

    def _create_equal_distribution(self, track_count: int) -> Dict[str, int]:
        """Create equal distribution across all phases.

        Args:
            track_count: Number of tracks to distribute

        Returns:
            Equal distribution with remainder in 'mid'
        """
        all_phases = ["opening", "build", "mid", "high", "descent", "closure"]
        tracks_per_phase = track_count // len(all_phases)
        distribution = {phase: tracks_per_phase for phase in all_phases}
        distribution["mid"] += track_count % len(all_phases)
        return distribution

    def _adjust_to_exact_count(self, distribution: Dict[str, int], target_count: int) -> Dict[str, int]:
        """Adjust distribution to match exact track count.

        Args:
            distribution: Current distribution
            target_count: Target number of tracks

        Returns:
            Adjusted distribution with exact count
        """
        diff = target_count - sum(distribution.values())
        
        if diff != 0:
            # Adjust the largest phase (or 'mid' if all are zero)
            largest_phase = max(distribution, key=distribution.get) if any(distribution.values()) else "mid"
            distribution[largest_phase] = max(0, distribution[largest_phase] + diff)
        
        return distribution

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

