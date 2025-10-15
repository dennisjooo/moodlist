"""Prompt templates for orchestrator operations."""

from .quality_evaluation import get_quality_evaluation_prompt
from .strategy_decision import get_strategy_decision_prompt

__all__ = [
    "get_quality_evaluation_prompt",
    "get_strategy_decision_prompt"
]