"""Helpers for serializing workflow status responses."""

from typing import Any, Dict, Optional

from ...core.constants import PlaylistStatus
from ...models.playlist import Playlist


def _merge_cost_summary(
    payload: Dict[str, Any], cost_summary: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Attach LLM cost metrics to the response payload if available."""

    if not cost_summary:
        return payload

    payload.update(
        {
            "total_llm_cost_usd": cost_summary.get("total_cost_usd"),
            "total_prompt_tokens": cost_summary.get("total_prompt_tokens"),
            "total_completion_tokens": cost_summary.get("total_completion_tokens"),
            "total_tokens": cost_summary.get("total_tokens"),
        }
    )
    return payload


def serialize_workflow_state(
    session_id: str,
    state,
    cost_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Serialize in-memory workflow state into an API response."""

    payload = {
        "session_id": session_id,
        "status": state.status.value,
        "current_step": state.current_step,
        "mood_prompt": state.mood_prompt,
        "mood_analysis": state.mood_analysis,
        "recommendation_count": len(state.recommendations),
        "seed_track_count": len(state.seed_tracks),
        "user_top_tracks_count": len(state.user_top_tracks),
        "user_top_artists_count": len(state.user_top_artists),
        "has_playlist": state.playlist_id is not None,
        "awaiting_input": state.awaiting_user_input,
        "error": state.error_message,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "metadata": {
            "iteration": state.metadata.get("iteration"),
            "cohesion_score": state.metadata.get("cohesion_score"),
        },
    }

    return _merge_cost_summary(payload, cost_summary)


def serialize_playlist_status(
    session_id: str,
    playlist: Playlist,
    cost_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Serialize persisted playlist details when workflow state is unavailable."""

    recommendation_count = getattr(playlist, "recommendation_count", None)
    if recommendation_count is None:
        recommendation_count = len(playlist.recommendations_data or [])

    payload = {
        "session_id": session_id,
        "status": playlist.status,
        "current_step": (
            "completed" if playlist.status == PlaylistStatus.COMPLETED else playlist.status
        ),
        "mood_prompt": playlist.mood_prompt,
        "mood_analysis": playlist.mood_analysis_data,
        "recommendation_count": recommendation_count,
        "has_playlist": playlist.spotify_playlist_id is not None,
        "awaiting_input": False,
        "error": playlist.error_message,
        "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
        "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
    }

    return _merge_cost_summary(payload, cost_summary)
