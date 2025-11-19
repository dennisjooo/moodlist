"""Phase scoring logic for playlist ordering."""

from typing import Any, Dict

from ...states.agent_state import TrackRecommendation


class PhaseScorer:
    """Calculates suitability scores for each phase."""

    def calculate_phase_scores(
        self, recommendation: TrackRecommendation, analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate suitability scores for each phase.

        Args:
            recommendation: Track recommendation
            analysis: Track energy analysis

        Returns:
            Dictionary mapping phase names to scores
        """
        # Extract analysis metrics
        energy = analysis.get("energy_level", 50)
        momentum = analysis.get("momentum", 50)
        emotional_intensity = analysis.get("emotional_intensity", 50)
        opening_potential = analysis.get("opening_potential", 50)
        closing_potential = analysis.get("closing_potential", 50)
        peak_potential = analysis.get("peak_potential", 50)
        llm_phase = analysis.get("phase_assignment")

        # Calculate base scores for each phase
        scores = {
            "opening": self._score_opening(energy, opening_potential, llm_phase),
            "build": self._score_build(energy, momentum, llm_phase),
            "mid": self._score_mid(energy, momentum, llm_phase),
            "high": self._score_high(energy, peak_potential, llm_phase),
            "descent": self._score_descent(
                energy, momentum, emotional_intensity, llm_phase
            ),
            "closure": self._score_closure(energy, closing_potential, llm_phase),
        }

        # Boost score for LLM-assigned phase
        if llm_phase and llm_phase in scores:
            scores[llm_phase] *= 1.5

        return scores

    def _score_opening(
        self, energy: float, opening_potential: float, llm_phase: str
    ) -> float:
        """Calculate opening phase score."""
        if not llm_phase or llm_phase == "opening":
            return opening_potential * 1.5
        return opening_potential * 0.5

    def _score_build(self, energy: float, momentum: float, llm_phase: str) -> float:
        """Calculate build phase score."""
        if energy < 70:
            return momentum * 0.8 + energy * 0.5
        return momentum * 0.3

    def _score_mid(self, energy: float, momentum: float, llm_phase: str) -> float:
        """Calculate mid phase score."""
        return (100 - abs(energy - 60)) * 0.7 + momentum * 0.5

    def _score_high(
        self, energy: float, peak_potential: float, llm_phase: str
    ) -> float:
        """Calculate high phase score."""
        if energy > 60:
            return peak_potential * 1.5 + energy * 0.5
        return peak_potential * 0.5

    def _score_descent(
        self, energy: float, momentum: float, emotional_intensity: float, llm_phase: str
    ) -> float:
        """Calculate descent phase score."""
        if energy < 70:
            return (100 - momentum) * 0.7 + emotional_intensity * 0.5
        return (100 - momentum) * 0.3

    def _score_closure(
        self, energy: float, closing_potential: float, llm_phase: str
    ) -> float:
        """Calculate closure phase score."""
        if not llm_phase or llm_phase == "closure":
            return closing_potential * 1.5
        return closing_potential * 0.5
