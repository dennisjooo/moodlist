"""Prompt templates for playlist ordering and energy flow analysis.

This module re-exports prompt functions from specialized submodules for backward compatibility.
"""

from .ordering_strategy_prompts import (
    get_ordering_strategy_system_prompt,
    get_ordering_strategy_user_prompt,
)
from .track_energy_prompts import (
    get_track_energy_analysis_system_prompt,
    get_track_energy_analysis_user_prompt,
)

__all__ = [
    "get_track_energy_analysis_system_prompt",
    "get_track_energy_analysis_user_prompt",
    "get_ordering_strategy_system_prompt",
    "get_ordering_strategy_user_prompt",
]
