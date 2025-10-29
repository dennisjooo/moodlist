"""Phase sorting logic for playlist ordering."""

import structlog
from typing import Any, Dict, List

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class PhaseSorter:
    """Handles sorting of tracks within phases for smooth transitions."""

    def sort_tracks_within_phase(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]],
        phase: str
    ) -> List[TrackRecommendation]:
        """Sort tracks within a phase for smooth transitions.

        Args:
            tracks: Tracks in the phase
            analysis_map: Track analyses
            phase: Phase name

        Returns:
            Sorted tracks
        """
        if len(tracks) <= 1:
            return tracks

        # Use phase-specific sorting strategy
        sorter = self._get_phase_sorter(phase)
        return sorter(tracks, analysis_map)

    def _get_phase_sorter(self, phase: str):
        """Get the appropriate sorting function for a phase."""
        sorters = {
            "opening": self._sort_opening,
            "build": self._sort_build,
            "mid": self._sort_mid,
            "high": self._sort_high,
            "descent": self._sort_descent,
            "closure": self._sort_closure,
        }
        return sorters.get(phase, self._sort_mid)

    def _sort_opening(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort opening phase - start with most welcoming, gradually build."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("opening_potential", 50),
            reverse=True
        )

    def _sort_build(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort build phase - gradually increase energy."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("energy_level", 50)
        )

    def _sort_mid(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort mid phase - maintain consistent energy, vary by emotional intensity."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("emotional_intensity", 50),
            reverse=True
        )

    def _sort_high(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort high phase - keep peak energy, vary to maintain interest."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("peak_potential", 50),
            reverse=True
        )

    def _sort_descent(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort descent phase - gradually decrease energy."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("energy_level", 50),
            reverse=True
        )

    def _sort_closure(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]]
    ) -> List[TrackRecommendation]:
        """Sort closure phase - end with most satisfying resolution."""
        return sorted(
            tracks,
            key=lambda t: analysis_map.get(t.track_id, {}).get("closing_potential", 50),
            reverse=True
        )

