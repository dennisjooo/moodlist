"""Energy analysis logic for tracks."""

import structlog
from typing import Any, Dict, List

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class EnergyAnalyzer:
    """Provides fallback energy analysis based on audio features."""

    def analyze_from_audio_features(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[Dict[str, Any]]:
        """Provide fallback energy analysis based on audio features.

        Args:
            recommendations: Track recommendations

        Returns:
            Basic energy analyses
        """
        logger.info("Using fallback energy analysis based on audio features")

        analyses = []
        for rec in recommendations:
            analysis = self._analyze_single_track(rec)
            analyses.append(analysis)

        return analyses

    def _analyze_single_track(
        self,
        rec: TrackRecommendation
    ) -> Dict[str, Any]:
        """Analyze a single track's energy characteristics.

        Args:
            rec: Track recommendation

        Returns:
            Energy analysis for the track
        """
        features = rec.audio_features or {}

        # Extract Spotify audio features
        energy = features.get("energy", 0.5) * 100
        tempo = features.get("tempo", 120)
        valence = features.get("valence", 0.5) * 100
        danceability = features.get("danceability", 0.5) * 100

        # Calculate derived metrics
        energy_level = energy
        momentum = (tempo / 200 * 100 + danceability) / 2
        emotional_intensity = (abs(valence - 50) * 2 + energy) / 2

        # Calculate potentials
        opening_potential = self._calculate_opening_potential(energy_level)
        closing_potential = self._calculate_closing_potential(energy_level, valence)
        peak_potential = self._calculate_peak_potential(energy_level)

        # Assign phase
        phase = self._assign_phase_from_energy(energy_level, opening_potential)

        return {
            "track_id": rec.track_id,
            "track_name": f"{rec.track_name} - {rec.artists[0] if rec.artists else 'Unknown'}",
            "energy_level": energy_level,
            "momentum": momentum,
            "emotional_intensity": emotional_intensity,
            "opening_potential": opening_potential,
            "closing_potential": closing_potential,
            "peak_potential": peak_potential,
            "phase_assignment": phase,
            "reasoning": "Fallback analysis based on audio features"
        }

    def _calculate_opening_potential(self, energy_level: float) -> float:
        """Calculate opening potential score."""
        return 60 if 40 < energy_level < 70 else 40

    def _calculate_closing_potential(self, energy_level: float, valence: float) -> float:
        """Calculate closing potential score."""
        return 70 if energy_level < 50 or valence > 60 else 40

    def _calculate_peak_potential(self, energy_level: float) -> float:
        """Calculate peak potential score."""
        return energy_level if energy_level > 70 else 40

    def _assign_phase_from_energy(
        self,
        energy_level: float,
        opening_potential: float
    ) -> str:
        """Assign phase based on energy level."""
        if energy_level < 40:
            return "opening" if opening_potential > 50 else "closure"
        elif energy_level < 60:
            return "build"
        elif energy_level < 75:
            return "mid"
        else:
            return "high"

