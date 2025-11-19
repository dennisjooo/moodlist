"""Playlist validator component for validating playlist creation requirements."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...states.agent_state import AgentState


class PlaylistValidator:
    """Handles validation of playlist creation requirements."""

    def __init__(self):
        """Initialize the playlist validator."""
        pass

    def validate_playlist_requirements(self, state: "AgentState") -> List[str]:
        """Validate that playlist creation requirements are met.

        Args:
            state: Current agent state

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not state.recommendations:
            errors.append("No recommendations available for playlist")

        if not state.metadata.get("spotify_access_token"):
            errors.append("No Spotify access token available")

        if not state.mood_prompt:
            errors.append("No mood prompt specified")

        return errors
