"""Service for editing completed/saved playlists."""

import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from ...models.playlist import Playlist
from ...agents.states.agent_state import TrackRecommendation
from ...core.exceptions import NotFoundException, ForbiddenException, ValidationException
from .spotify_edit_service import SpotifyEditService

logger = structlog.get_logger(__name__)


class CompletedPlaylistEditor:
    """Handles editing of playlists that have been saved to Spotify."""

    def __init__(self):
        """Initialize the completed playlist editor."""
        self.spotify_edit_service = SpotifyEditService()
        # Dictionary to store locks per session_id to prevent concurrent edits
        self._edit_locks: Dict[str, asyncio.Lock] = {}

    async def edit_playlist(
        self,
        session_id: str,
        edit_type: str,
        db: AsyncSession,
        access_token: str,
        user_id: int,
        track_id: Optional[str] = None,
        new_position: Optional[int] = None,
        track_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """Edit a completed playlist with per-session locking to prevent race conditions.

        Args:
            session_id: Workflow session ID
            edit_type: Type of edit (reorder/remove/add)
            db: Database session
            access_token: Spotify access token
            user_id: User ID for permission check
            track_id: Track ID for edit
            new_position: New position for reorder operations
            track_uri: Track URI for add operations

        Returns:
            Result dictionary with updated playlist info

        Raises:
            ValueError: If playlist not found or user doesn't have permission
        """
        # Get or create a lock for this session_id to prevent concurrent edits
        if session_id not in self._edit_locks:
            self._edit_locks[session_id] = asyncio.Lock()
        
        async with self._edit_locks[session_id]:
            try:
                # Load playlist from database
                query = select(Playlist).where(Playlist.session_id == session_id)
                result = await db.execute(query)
                playlist = result.scalar_one_or_none()

                if not playlist:
                    raise NotFoundException("Playlist", session_id)

                # Validate user owns this playlist
                if playlist.user_id != user_id:
                    raise ForbiddenException("You don't have permission to edit this playlist")

                # Check if playlist has been saved to Spotify
                is_saved_to_spotify = bool(playlist.spotify_playlist_id)

                # Get current recommendations
                recommendations = playlist.recommendations_data or []

                # Apply edit based on type
                if edit_type == "remove":
                    recommendations = await self._handle_remove(
                        recommendations,
                        playlist.spotify_playlist_id,
                        track_id,
                        access_token,
                        is_saved_to_spotify
                    )
                elif edit_type == "reorder":
                    recommendations = await self._handle_reorder(
                        recommendations,
                        playlist.spotify_playlist_id,
                        track_id,
                        new_position,
                        access_token,
                        is_saved_to_spotify
                    )
                elif edit_type == "add":
                    recommendations = await self._handle_add(
                        recommendations,
                        playlist.spotify_playlist_id,
                        track_uri,
                        new_position,
                        access_token,
                        is_saved_to_spotify
                    )
                else:
                    raise ValidationException(f"Invalid edit_type: {edit_type}. Must be one of: reorder, remove, add")

                # Update database with modified recommendations
                playlist.recommendations_data = recommendations
                playlist.track_count = len(recommendations)  # Update track count to match recommendations
                flag_modified(playlist, "recommendations_data")
                playlist.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(playlist)

                return {
                    "session_id": session_id,
                    "status": "success",
                    "edit_type": edit_type,
                    "recommendation_count": len(recommendations),
                    "message": f"Successfully applied {edit_type} edit to playlist"
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to edit playlist {session_id}: {str(e)}")
                raise

    async def _handle_remove(
        self,
        recommendations: List[Dict],
        spotify_playlist_id: Optional[str],
        track_id: str,
        access_token: str,
        is_saved_to_spotify: bool
    ) -> List[Dict]:
        """Handle remove edit."""
        if not track_id:
            raise ValidationException("track_id is required for remove operation")

        # Find and remove track
        track_to_remove = None
        for i, rec in enumerate(recommendations):
            if rec.get("track_id") == track_id:
                track_to_remove = recommendations.pop(i)
                break

        if not track_to_remove:
            raise NotFoundException("Track", track_id)

        # Remove from Spotify if playlist is saved
        if is_saved_to_spotify:
            await self.spotify_edit_service.remove_track_from_spotify(
                spotify_playlist_id,
                track_to_remove.get("spotify_uri"),
                access_token
            )
            logger.info(f"Removed track {track_id} from Spotify playlist {spotify_playlist_id}")
        else:
            logger.info(f"Removed track {track_id} from draft playlist (not yet in Spotify)")

        return recommendations

    async def _handle_reorder(
        self,
        recommendations: List[Dict],
        spotify_playlist_id: Optional[str],
        track_id: str,
        new_position: int,
        access_token: str,
        is_saved_to_spotify: bool
    ) -> List[Dict]:
        """Handle reorder edit."""
        if track_id is None or new_position is None:
            raise ValidationException("track_id and new_position are required for reorder operation")

        # Find track index
        old_index = None
        for i, rec in enumerate(recommendations):
            if rec.get("track_id") == track_id:
                old_index = i
                break

        if old_index is None:
            raise NotFoundException("Track", track_id)

        # Reorder in local list
        track = recommendations.pop(old_index)
        recommendations.insert(new_position, track)

        # Reorder in Spotify if playlist is saved
        if is_saved_to_spotify:
            await self.spotify_edit_service.reorder_track_in_spotify(
                spotify_playlist_id,
                old_index,
                new_position,
                access_token
            )
            logger.info(f"Reordered track {track_id} from position {old_index} to {new_position} in Spotify")
        else:
            logger.info(f"Reordered track {track_id} from position {old_index} to {new_position} in draft")

        return recommendations

    async def _handle_add(
        self,
        recommendations: List[Dict],
        spotify_playlist_id: Optional[str],
        track_uri: str,
        new_position: Optional[int],
        access_token: str,
        is_saved_to_spotify: bool
    ) -> List[Dict]:
        """Handle add edit."""
        if not track_uri:
            raise ValidationException("track_uri is required for add operation")

        # Extract track ID from URI (format: spotify:track:ID)
        track_id_from_uri = track_uri.split(":")[-1]

        # Get track details
        track_data = await self.spotify_edit_service.get_track_details(
            track_id_from_uri,
            access_token
        )

        # Add to local recommendations
        new_track = {
            "track_id": track_data["id"],
            "track_name": track_data["name"],
            "artists": [artist["name"] for artist in track_data["artists"]],
            "spotify_uri": track_data["uri"],
            "confidence_score": 0.5,
            "reasoning": "Added by user",
            "source": "user_added"
        }

        # Add to position or end of list
        if new_position is not None:
            recommendations.insert(new_position, new_track)
        else:
            recommendations.append(new_track)

        # Add to Spotify if playlist is saved
        if is_saved_to_spotify:
            await self.spotify_edit_service.add_track_to_spotify(
                spotify_playlist_id,
                track_uri,
                access_token,
                new_position
            )
            logger.info(f"Added track {track_uri} to Spotify playlist {spotify_playlist_id}")
        else:
            logger.info(f"Added track {track_uri} to draft playlist (not yet in Spotify)")

        return recommendations

    async def update_in_memory_state(
        self,
        workflow_manager,
        session_id: str,
        recommendations: List[Dict]
    ) -> None:
        """Update in-memory workflow state if it exists.

        Args:
            workflow_manager: Workflow manager instance
            session_id: Session ID
            recommendations: Updated recommendations list
        """
        state = workflow_manager.get_workflow_state(session_id)
        if state:
            # Update the in-memory recommendations to match database
            state.recommendations = [
                TrackRecommendation(
                    track_id=rec["track_id"],
                    track_name=rec["track_name"],
                    artists=rec["artists"],
                    spotify_uri=rec.get("spotify_uri"),
                    confidence_score=rec.get("confidence_score", 0.5),
                    reasoning=rec.get("reasoning", ""),
                    source=rec.get("source", "unknown")
                )
                for rec in recommendations
            ]
            logger.info(f"Updated in-memory state for session {session_id}")

