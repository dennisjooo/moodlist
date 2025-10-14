"""Playlist namer component for generating creative playlist names."""

import logging
import random
import re
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from .prompts import get_playlist_naming_prompt

logger = logging.getLogger(__name__)


class PlaylistNamer:
    """Handles playlist name generation using LLM or fallback methods."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """Initialize the playlist namer.

        Args:
            llm: Language model for creative naming
        """
        self.llm = llm

    async def generate_name(self, mood_prompt: str, track_count: int) -> str:
        """Generate a creative playlist name based on mood.

        Args:
            mood_prompt: User's mood description
            track_count: Number of tracks in the playlist

        Returns:
            Generated playlist name
        """
        try:
            # Use LLM for creative playlist naming if available
            if self.llm:
                name = await self._generate_name_with_llm(mood_prompt, track_count)
            else:
                name = self._generate_name_fallback(mood_prompt)

            # Ensure name is not too long for Spotify (100 chars max)
            if len(name) > 100:
                name = name[:97] + "..."

            return name

        except Exception as e:
            logger.error(f"Error generating playlist name: {str(e)}")
            return self._generate_name_fallback(mood_prompt)

    async def _generate_name_with_llm(self, mood_prompt: str, track_count: int) -> str:
        """Generate playlist name using LLM.

        Args:
            mood_prompt: User's mood description
            track_count: Number of tracks in the playlist

        Returns:
            LLM-generated playlist name
        """
        try:
            prompt = get_playlist_naming_prompt(mood_prompt, track_count)

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            name = response.content.strip() if hasattr(response, 'content') else str(response).strip()

            # Clean up the name
            name = re.sub(r'^["\']|["\']$', '', name)  # Remove quotes
            name = re.sub(r'^Playlist:\s*', '', name, flags=re.IGNORECASE)  # Remove "Playlist:" prefix

            return name or self._generate_name_fallback(mood_prompt)

        except Exception as e:
            logger.error(f"LLM name generation failed: {str(e)}")
            return self._generate_name_fallback(mood_prompt)

    def _generate_name_fallback(self, mood_prompt: str) -> str:
        """Generate a fallback playlist name.

        Args:
            mood_prompt: User's mood description

        Returns:
            Fallback playlist name
        """
        mood_prompt_lower = mood_prompt.lower()

        # Mood-based name templates
        name_templates = {
            "chill": ["Chill Vibes", "Relaxed Moments", "Easy Listening"],
            "energetic": ["Energy Boost", "Power Hour", "High Energy"],
            "happy": ["Feel Good", "Happy Days", "Positive Vibes"],
            "sad": ["Emotional", "Melancholy", "Deep Thoughts"],
            "romantic": ["Love Songs", "Romantic Evening", "Date Night"],
            "focus": ["Concentration", "Study Mode", "Focus Flow"],
            "party": ["Party Time", "Celebration", "Dance Party"],
            "workout": ["Workout Mix", "Fitness Fuel", "Gym Session"]
        }

        # Find matching template
        for mood, names in name_templates.items():
            if mood in mood_prompt_lower:
                return random.choice(names)

        # Default names if no mood matches
        default_names = [
            "Mood Mix",
            "Curated Sounds",
            "Vibe Session",
            "Music Journey",
            "Sonic Escape"
        ]

        return random.choice(default_names)