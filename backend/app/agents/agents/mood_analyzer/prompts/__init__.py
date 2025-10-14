"""Prompt templates for mood analysis."""

from .mood_analysis import (
    get_mood_analysis_system_prompt,
)
from .artist_filtering import get_artist_filtering_prompt

__all__ = [
    "get_mood_analysis_system_prompt",
    "get_artist_filtering_prompt"
]