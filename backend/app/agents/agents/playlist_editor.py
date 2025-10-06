"""Playlist editor agent for human-in-the-loop editing capabilities."""

import logging
from typing import Any, Dict, List, Optional

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus, PlaylistEdit, TrackRecommendation


logger = logging.getLogger(__name__)


class PlaylistEditorAgent(BaseAgent):
    """Agent for handling human-in-the-loop playlist editing."""

    def __init__(
        self,
        verbose: bool = False
    ):
        """Initialize the playlist editor agent.

        Args:
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="playlist_editor",
            description="Handles human-in-the-loop editing of generated playlists",
            verbose=verbose
        )

    async def execute(self, state: AgentState) -> AgentState:
        """Execute playlist editing based on user input.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with edits applied
        """
        try:
            logger.info(f"Processing playlist edits for session {state.session_id}")

            # Check if there are pending edits
            if not state.awaiting_user_input or not state.user_edits:
                logger.info("No user edits to process")
                return state

            # Apply the latest edit
            latest_edit = state.user_edits[-1]  # Get most recent edit

            if latest_edit.edit_type == "reorder":
                state.recommendations = await self._apply_reorder_edit(
                    state.recommendations, latest_edit
                )
            elif latest_edit.edit_type == "remove":
                state.recommendations = await self._apply_remove_edit(
                    state.recommendations, latest_edit
                )
            elif latest_edit.edit_type == "add":
                state.recommendations = await self._apply_add_edit(
                    state.recommendations, latest_edit, state
                )
            elif latest_edit.edit_type == "replace":
                state.recommendations = await self._apply_replace_edit(
                    state.recommendations, latest_edit, state
                )

            # Update state
            state.current_step = "edits_applied"
            state.status = RecommendationStatus.PROCESSING_EDITS
            state.awaiting_user_input = False

            # Store edit metadata
            state.metadata["total_edits"] = len(state.user_edits)
            state.metadata["last_edit_type"] = latest_edit.edit_type
            state.metadata["last_edit_timestamp"] = latest_edit.edit_timestamp.isoformat()

            logger.info(f"Applied {latest_edit.edit_type} edit to playlist")

        except Exception as e:
            logger.error(f"Error in playlist editing: {str(e)}", exc_info=True)
            state.set_error(f"Playlist editing failed: {str(e)}")

        return state

    async def _apply_reorder_edit(
        self,
        recommendations: List[TrackRecommendation],
        edit: PlaylistEdit
    ) -> List[TrackRecommendation]:
        """Apply a reorder edit to the playlist.

        Args:
            recommendations: Current recommendations
            edit: Reorder edit to apply

        Returns:
            Updated recommendations list
        """
        if not edit.track_id or edit.new_position is None:
            logger.warning("Invalid reorder edit: missing track_id or new_position")
            return recommendations

        # Find the track to move
        track_to_move = None
        track_index = None

        for i, rec in enumerate(recommendations):
            if rec.track_id == edit.track_id:
                track_to_move = rec
                track_index = i
                break

        if track_to_move is None:
            logger.warning(f"Track {edit.track_id} not found for reordering")
            return recommendations

        # Remove track from current position
        recommendations.pop(track_index)

        # Insert at new position
        new_position = min(edit.new_position, len(recommendations))
        recommendations.insert(new_position, track_to_move)

        # Update confidence scores based on new positions
        for i, rec in enumerate(recommendations):
            # Slightly adjust confidence based on user preference (position)
            position_bonus = (len(recommendations) - i) * 0.01  # Higher position = slight bonus
            rec.confidence_score = min(rec.confidence_score + position_bonus, 1.0)

        logger.info(f"Reordered track {edit.track_id} to position {edit.new_position}")

        return recommendations

    async def _apply_remove_edit(
        self,
        recommendations: List[TrackRecommendation],
        edit: PlaylistEdit
    ) -> List[TrackRecommendation]:
        """Apply a remove edit to the playlist.

        Args:
            recommendations: Current recommendations
            edit: Remove edit to apply

        Returns:
            Updated recommendations list
        """
        if not edit.track_id:
            logger.warning("Invalid remove edit: missing track_id")
            return recommendations

        # Find and remove the track
        original_count = len(recommendations)
        recommendations = [
            rec for rec in recommendations
            if rec.track_id != edit.track_id
        ]

        removed_count = original_count - len(recommendations)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} track(s) with ID {edit.track_id}")
        else:
            logger.warning(f"Track {edit.track_id} not found for removal")

        return recommendations

    async def _apply_add_edit(
        self,
        recommendations: List[TrackRecommendation],
        edit: PlaylistEdit,
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Apply an add edit to the playlist.

        Args:
            recommendations: Current recommendations
            edit: Add edit to apply
            state: Current agent state

        Returns:
            Updated recommendations list
        """
        # For now, adding tracks requires additional API calls
        # This would typically involve calling RecoBeat API for new recommendations
        # based on the current playlist context

        logger.info(f"Add edit requested, but add functionality requires additional API integration")
        logger.info(f"Edit details: {edit.reasoning}")

        # In a full implementation, this would:
        # 1. Extract current playlist characteristics
        # 2. Call RecoBeat API for similar tracks
        # 3. Add the new tracks to the playlist

        return recommendations

    async def _apply_replace_edit(
        self,
        recommendations: List[TrackRecommendation],
        edit: PlaylistEdit,
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Apply a replace edit to the playlist.

        Args:
            recommendations: Current recommendations
            edit: Replace edit to apply
            state: Current agent state

        Returns:
            Updated recommendations list
        """
        # Similar to add, but replaces a specific track
        logger.info(f"Replace edit requested for track {edit.track_id}")

        # In a full implementation, this would:
        # 1. Find the track to replace
        # 2. Get recommendations similar to the replacement target
        # 3. Replace the track with a better match

        return recommendations

    def create_edit_from_request(
        self,
        edit_type: str,
        track_id: Optional[str] = None,
        new_position: Optional[int] = None,
        reasoning: Optional[str] = None
    ) -> PlaylistEdit:
        """Create a PlaylistEdit object from user request.

        Args:
            edit_type: Type of edit (reorder, remove, add, replace)
            track_id: ID of track being edited
            new_position: New position for reorder operations
            reasoning: User's reasoning for the edit

        Returns:
            PlaylistEdit object
        """
        return PlaylistEdit(
            edit_type=edit_type,
            track_id=track_id,
            new_position=new_position,
            reasoning=reasoning
        )

    def validate_edit(
        self,
        edit: PlaylistEdit,
        recommendations: List[TrackRecommendation]
    ) -> bool:
        """Validate that an edit can be applied.

        Args:
            edit: Edit to validate
            recommendations: Current recommendations

        Returns:
            Whether the edit is valid
        """
        if edit.edit_type == "reorder":
            if not edit.track_id or edit.new_position is None:
                return False

            # Check if track exists
            track_exists = any(rec.track_id == edit.track_id for rec in recommendations)
            if not track_exists:
                return False

            # Check if position is valid
            if edit.new_position < 0 or edit.new_position > len(recommendations):
                return False

        elif edit.edit_type == "remove":
            if not edit.track_id:
                return False

            # Check if track exists
            track_exists = any(rec.track_id == edit.track_id for rec in recommendations)
            if not track_exists:
                return False

        elif edit.edit_type == "add":
            # Add validation would depend on implementation
            pass

        elif edit.edit_type == "replace":
            # Replace validation would depend on implementation
            pass

        return True

    def get_playlist_summary(self, recommendations: List[TrackRecommendation]) -> Dict[str, Any]:
        """Get a summary of the current playlist state.

        Args:
            recommendations: Current recommendations

        Returns:
            Playlist summary
        """
        if not recommendations:
            return {"track_count": 0, "total_duration": 0}

        # Calculate total duration (would need actual duration data)
        total_duration = sum(
            rec.audio_features.get("duration_ms", 0) if rec.audio_features else 0
            for rec in recommendations
        )

        # Get unique artists
        all_artists = []
        for rec in recommendations:
            all_artists.extend(rec.artists)

        unique_artists = list(set(all_artists))

        return {
            "track_count": len(recommendations),
            "total_duration_ms": total_duration,
            "total_duration_minutes": total_duration / 60000,
            "unique_artists": len(unique_artists),
            "top_artists": self._get_top_artists(recommendations),
            "average_confidence": sum(rec.confidence_score for rec in recommendations) / len(recommendations)
        }

    def _get_top_artists(self, recommendations: List[TrackRecommendation], limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most frequent artists in the playlist.

        Args:
            recommendations: Current recommendations
            limit: Maximum number of artists to return

        Returns:
            List of top artists with counts
        """
        artist_counts = {}

        for rec in recommendations:
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

        # Sort by count and take top artists
        top_artists = sorted(
            artist_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"artist": artist, "track_count": count}
            for artist, count in top_artists
        ]