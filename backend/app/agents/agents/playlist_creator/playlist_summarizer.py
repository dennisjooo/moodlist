"""Playlist summarizer component for generating playlist summaries."""

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ...states.agent_state import AgentState


class PlaylistSummarizer:
    """Handles generation of playlist summaries."""

    def __init__(self):
        """Initialize the playlist summarizer."""
        pass

    def get_playlist_summary(self, state: "AgentState") -> Dict[str, Any]:
        """Get a summary of the created playlist.

        Args:
            state: Current agent state

        Returns:
            Playlist summary
        """
        if not state.playlist_id:
            return {"status": "not_created"}

        return {
            "playlist_id": state.playlist_id,
            "playlist_name": state.playlist_name,
            "spotify_url": state.metadata.get("playlist_url"),
            "spotify_uri": state.metadata.get("playlist_uri"),
            "track_count": len(state.recommendations),
            "mood_prompt": state.mood_prompt,
            "created_at": state.updated_at.isoformat(),
            "status": state.status.value
        }