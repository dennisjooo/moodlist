"""Playlist describer component for generating playlist descriptions."""

import structlog
import re
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from .prompts import get_playlist_description_prompt

logger = structlog.get_logger(__name__)


class PlaylistDescriber:
    """Handles playlist description generation using LLM or fallback methods."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """Initialize the playlist describer.

        Args:
            llm: Language model for creative descriptions
        """
        self.llm = llm

    async def generate_description(self, mood_prompt: str, track_count: int) -> str:
        """Generate a descriptive playlist description using LLM.

        Args:
            mood_prompt: User's mood description
            track_count: Number of tracks in the playlist

        Returns:
            Generated playlist description
        """
        try:
            # Use LLM for creative description if available
            if self.llm:
                description = await self._generate_description_with_llm(
                    mood_prompt, track_count
                )
            else:
                description = self._generate_description_fallback(
                    mood_prompt, track_count
                )

            return description

        except Exception as e:
            logger.error(f"Error generating playlist description: {str(e)}")
            # Fallback to simple description
            return f"Mood-based playlist with {track_count} tracks curated with love by MoodList"

    async def _generate_description_with_llm(
        self, mood_prompt: str, track_count: int
    ) -> str:
        """Generate playlist description using LLM.

        Args:
            mood_prompt: User's mood description
            track_count: Number of tracks in the playlist

        Returns:
            LLM-generated playlist description
        """
        try:
            prompt = get_playlist_description_prompt(mood_prompt, track_count)

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            description = (
                response.content.strip()
                if hasattr(response, "content")
                else str(response).strip()
            )

            # Clean up the description
            description = re.sub(r'^["\']|["\']$', "", description)  # Remove quotes

            # Ensure it ends with the required format
            required_ending = f"{track_count} tracks curated with love by MoodList"
            if not description.endswith(required_ending):
                # Remove any existing ending and add the correct one
                description = re.sub(r"\s*\d+\s*tracks.*$", "", description).strip()
                description += f" {required_ending}"

            # Cap at 200 characters
            if len(description) > 200:
                description = description[:197] + "..."

            return description or self._generate_description_fallback(
                mood_prompt, track_count
            )

        except Exception as e:
            logger.error(f"LLM description generation failed: {str(e)}")
            return self._generate_description_fallback(mood_prompt, track_count)

    def _generate_description_fallback(self, mood_prompt: str, track_count: int) -> str:
        """Generate a fallback playlist description.

        Args:
            mood_prompt: User's mood description
            track_count: Number of tracks in the playlist

        Returns:
            Fallback playlist description
        """
        try:
            # Use mood analysis if available for richer description
            # For now, use simple mood-based description
            description = f"Perfect {mood_prompt} soundtrack"

            # Add the required ending
            full_description = (
                f"{description}. {track_count} tracks curated with love by MoodList"
            )

            # Cap at 200 characters
            if len(full_description) > 200:
                # Truncate the description part to fit
                available_space = (
                    200
                    - len(f". {track_count} tracks curated with love by MoodList")
                    - 3
                )
                if available_space > 0:
                    description = description[:available_space] + "..."
                    full_description = f"{description}. {track_count} tracks curated with love by MoodList"
                else:
                    full_description = (
                        f"{track_count} tracks curated with love by MoodList"
                    )

            return full_description

        except Exception as e:
            logger.error(f"Fallback description generation failed: {str(e)}")
            return f"{track_count} tracks curated with love by MoodList"
