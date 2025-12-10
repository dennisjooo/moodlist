"""Strategy builder for determining ordering strategies."""

from typing import Any, Dict


class StrategyBuilder:
    """Builds default ordering strategies based on track characteristics."""

    def build_default_strategy(
        self, avg_energy: float, energy_range: float, track_count: int
    ) -> Dict[str, Any]:
        """Get default ordering strategy based on track characteristics.

        Args:
            avg_energy: Average energy level
            energy_range: Range of energy levels
            track_count: Number of tracks

        Returns:
            Default strategy
        """
        # Determine strategy type
        strategy_name = self._determine_strategy_type(avg_energy, energy_range)

        # Calculate phase distribution
        phase_dist = self._calculate_phase_distribution(strategy_name, track_count)

        return {
            "strategy": strategy_name,
            "reasoning": f"Default strategy based on avg_energy={avg_energy:.1f}, range={energy_range:.1f}",
            "phase_distribution": phase_dist,
            "special_considerations": [],
            "transition_notes": "Smooth transitions based on audio feature similarity",
        }

    def _determine_strategy_type(self, avg_energy: float, energy_range: float) -> str:
        """Determine the appropriate strategy type.

        Args:
            avg_energy: Average energy level
            energy_range: Range of energy levels

        Returns:
            Strategy name
        """
        if avg_energy > 75:
            return "sustained_energy"
        elif avg_energy < 35:
            return "ambient_flow"
        elif energy_range > 50:
            return "emotional_rollercoaster"
        else:
            return "classic_build"

    def _calculate_phase_distribution(
        self, strategy_name: str, track_count: int
    ) -> Dict[str, int]:
        """Calculate phase distribution for a strategy.

        Args:
            strategy_name: Name of the strategy
            track_count: Number of tracks

        Returns:
            Phase distribution
        """
        if strategy_name == "sustained_energy":
            return self._sustained_energy_distribution(track_count)
        elif strategy_name == "ambient_flow":
            return self._ambient_flow_distribution(track_count)
        else:  # classic_build or emotional_rollercoaster
            return self._classic_build_distribution(track_count)

    def _sustained_energy_distribution(self, track_count: int) -> Dict[str, int]:
        """Calculate distribution for sustained energy strategy."""
        return {
            "opening": max(1, track_count // 15),
            "build": max(2, track_count // 8),
            "mid": max(3, track_count // 4),
            "high": max(4, track_count // 3),
            "descent": max(2, track_count // 8),
            "closure": max(1, track_count // 15),
        }

    def _ambient_flow_distribution(self, track_count: int) -> Dict[str, int]:
        """Calculate distribution for ambient flow strategy."""
        return {
            "opening": max(2, track_count // 6),
            "build": max(3, track_count // 5),
            "mid": max(5, track_count // 3),
            "high": max(2, track_count // 8),
            "descent": max(3, track_count // 5),
            "closure": max(2, track_count // 6),
        }

    def _classic_build_distribution(self, track_count: int) -> Dict[str, int]:
        """Calculate distribution for classic build strategy."""
        return {
            "opening": max(1, track_count // 10),
            "build": max(3, track_count // 6),
            "mid": max(4, track_count // 5),
            "high": max(3, track_count // 6),
            "descent": max(2, track_count // 8),
            "closure": max(1, track_count // 10),
        }
