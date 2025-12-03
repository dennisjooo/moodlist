"""Remix service for creating playlist variations and managing remix workflows."""

from typing import Dict, Any, Optional, List
import structlog
import json

from app.models.playlist import Playlist
from app.repositories.playlist_repository import PlaylistRepository
from app.core.exceptions import NotFoundException, ValidationException

logger = structlog.get_logger(__name__)


class RemixService:
    """Service for managing playlist remixes and variations."""

    def __init__(self, playlist_repository: PlaylistRepository):
        """Initialize the remix service.

        Args:
            playlist_repository: Playlist repository for data access
        """
        self.playlist_repository = playlist_repository
        self.logger = logger.bind(service="RemixService")

    async def get_remix_options(
        self,
        playlist_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """Get available remix types and parameters for a playlist.

        Args:
            playlist_id: ID of the playlist to remix
            user_id: ID of the user requesting remixes

        Returns:
            Dictionary with available remix types and parameter options
        """
        playlist = await self.playlist_repository.get_by_id_and_user(playlist_id, user_id)
        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))

        mood_analysis = playlist.mood_analysis_data or {}

        return {
            "original_playlist_id": playlist_id,
            "original_mood": playlist.mood_prompt,
            "remix_types": [
                {
                    "type": "energy",
                    "name": "Energy Remix",
                    "description": "Adjust the energy level of the playlist",
                    "parameters": {
                        "energy_adjustment": {
                            "type": "slider",
                            "min": -50,
                            "max": 50,
                            "default": 20,
                            "step": 10,
                            "unit": "% adjustment",
                        }
                    },
                },
                {
                    "type": "mood",
                    "name": "Mood Remix",
                    "description": "Shift to a different emotional tone",
                    "parameters": {
                        "mood_shift": {
                            "type": "select",
                            "options": [
                                "happier",
                                "sadder",
                                "more_intense",
                                "more_chill",
                                "more_upbeat",
                            ],
                            "default": "happier",
                        }
                    },
                },
                {
                    "type": "tempo",
                    "name": "Tempo Remix",
                    "description": "Change the speed of the tracks",
                    "parameters": {
                        "tempo_adjustment": {
                            "type": "slider",
                            "min": -30,
                            "max": 30,
                            "default": 15,
                            "step": 5,
                            "unit": "% adjustment",
                        }
                    },
                },
                {
                    "type": "genre",
                    "name": "Genre Remix",
                    "description": "Explore a different genre while keeping the mood",
                    "parameters": {
                        "genre_shift": {
                            "type": "select",
                            "options": [
                                "electronic",
                                "acoustic",
                                "indie",
                                "hip_hop",
                                "pop",
                                "rock",
                                "jazz",
                            ],
                            "default": "electronic",
                        }
                    },
                },
                {
                    "type": "danceability",
                    "name": "Danceability Remix",
                    "description": "Make it more or less dancefloor-friendly",
                    "parameters": {
                        "danceability_adjustment": {
                            "type": "slider",
                            "min": -40,
                            "max": 40,
                            "default": 20,
                            "step": 10,
                            "unit": "% adjustment",
                        }
                    },
                },
            ],
            "current_analysis": {
                "primary_emotion": mood_analysis.get("primary_emotion"),
                "energy_level": mood_analysis.get("energy_level"),
                "tempo_bpm": mood_analysis.get("tempo_bpm"),
            },
        }

    async def create_remix(
        self,
        playlist_id: int,
        user_id: int,
        remix_type: str,
        remix_parameters: Dict[str, Any],
        new_mood_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a remix of an existing playlist.

        Args:
            playlist_id: ID of the playlist to remix
            user_id: ID of the user creating the remix
            remix_type: Type of remix (energy, mood, tempo, genre, danceability)
            remix_parameters: Parameters for the remix
            new_mood_prompt: Optional custom mood prompt for the remix

        Returns:
            Dictionary with remix metadata to pass to recommendation workflow
        """
        original_playlist = await self.playlist_repository.get_by_id_and_user(
            playlist_id, user_id
        )
        if not original_playlist:
            raise NotFoundException("Playlist", str(playlist_id))

        # Validate remix type
        valid_types = ["energy", "mood", "tempo", "genre", "danceability"]
        if remix_type not in valid_types:
            raise ValidationException(f"Invalid remix type: {remix_type}")

        # Generate new mood prompt based on remix type
        original_mood = original_playlist.mood_prompt
        mood_analysis = original_playlist.mood_analysis_data or {}

        if not new_mood_prompt:
            new_mood_prompt = self._generate_remix_prompt(
                original_mood, remix_type, remix_parameters, mood_analysis
            )

        self.logger.info(
            "remix_created",
            original_playlist_id=playlist_id,
            remix_type=remix_type,
            new_mood_prompt=new_mood_prompt,
        )

        return {
            "remix_type": remix_type,
            "remix_parameters": remix_parameters,
            "mood_prompt": new_mood_prompt,
            "parent_playlist_id": original_playlist.id,
            "is_remix": True,
            "remix_generation": original_playlist.remix_generation + 1,
            "original_mood_prompt": original_mood,
        }

    async def get_remix_chain(
        self,
        playlist_id: int,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """Get the remix chain/history for a playlist.

        Shows the lineage: Original → Remix 1 → Remix of Remix, etc.

        Args:
            playlist_id: ID of any playlist in the chain
            user_id: ID of the user

        Returns:
            List of playlists in the remix chain, ordered from original to current
        """
        playlist = await self.playlist_repository.get_by_id_and_user(playlist_id, user_id)
        if not playlist:
            raise NotFoundException("Playlist", str(playlist_id))

        chain = []
        current = playlist

        # Walk back to the original
        while current:
            chain.insert(
                0,
                {
                    "id": current.id,
                    "name": current.playlist_data.get("name", "Untitled")
                    if current.playlist_data
                    else "Untitled",
                    "mood_prompt": current.mood_prompt,
                    "is_remix": current.is_remix,
                    "remix_type": (
                        current.remix_parameters.get("type")
                        if current.remix_parameters
                        else None
                    ),
                    "remix_generation": current.remix_generation,
                    "created_at": current.created_at.isoformat()
                    if current.created_at
                    else None,
                },
            )
            current = current.parent_playlist

        return chain

    async def get_playlist_remixes(
        self,
        playlist_id: int,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all remixes that were created from a specific playlist.

        This shows what other playlists were derived from this one.

        Args:
            playlist_id: ID of the original playlist
            user_id: ID of the user

        Returns:
            List of remixes derived from this playlist
        """
        original_playlist = await self.playlist_repository.get_by_id_and_user(
            playlist_id, user_id
        )
        if not original_playlist:
            raise NotFoundException("Playlist", str(playlist_id))

        remixes = []
        for remix in original_playlist.remixes:
            if remix.deleted_at is None:  # Only include non-deleted remixes
                remixes.append(
                    {
                        "id": remix.id,
                        "name": remix.playlist_data.get("name", "Untitled")
                        if remix.playlist_data
                        else "Untitled",
                        "remix_type": (
                            remix.remix_parameters.get("type")
                            if remix.remix_parameters
                            else None
                        ),
                        "remix_generation": remix.remix_generation,
                        "created_at": remix.created_at.isoformat()
                        if remix.created_at
                        else None,
                        "track_count": remix.track_count,
                    }
                )

        return remixes

    def _generate_remix_prompt(
        self,
        original_mood: str,
        remix_type: str,
        remix_parameters: Dict[str, Any],
        mood_analysis: Dict[str, Any],
    ) -> str:
        """Generate a new mood prompt for a remix.

        Args:
            original_mood: Original playlist mood prompt
            remix_type: Type of remix to apply
            remix_parameters: Parameters for the remix
            mood_analysis: Original mood analysis data

        Returns:
            New mood prompt for the remix
        """
        if remix_type == "energy":
            energy_adj = remix_parameters.get("energy_adjustment", 20)
            direction = "more" if energy_adj > 0 else "less"
            return f"{original_mood}, but {direction} energetic and intense"

        elif remix_type == "mood":
            mood_shift = remix_parameters.get("mood_shift", "happier")
            mood_descriptions = {
                "happier": "uplifting, joyful, positive",
                "sadder": "melancholic, introspective, emotional",
                "more_intense": "powerful, driving, aggressive",
                "more_chill": "relaxed, mellow, laid-back",
                "more_upbeat": "upbeat, energetic, bouncy",
            }
            shift_desc = mood_descriptions.get(mood_shift, mood_shift)
            return f"{original_mood}, shifted to be more {shift_desc}"

        elif remix_type == "tempo":
            tempo_adj = remix_parameters.get("tempo_adjustment", 15)
            direction = "faster" if tempo_adj > 0 else "slower"
            return f"{original_mood}, but with {direction} tempo and pace"

        elif remix_type == "genre":
            genre_shift = remix_parameters.get("genre_shift", "electronic")
            return f"{original_mood}, reimagined in {genre_shift} style"

        elif remix_type == "danceability":
            dance_adj = remix_parameters.get("danceability_adjustment", 20)
            direction = "more" if dance_adj > 0 else "less"
            return f"{original_mood}, but {direction} dancefloor-friendly and groovy"

        return original_mood

    async def get_remix_statistics(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """Get remix statistics for a user.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with remix statistics
        """
        all_playlists = await self.playlist_repository.get_by_user(user_id)

        total_remixes = sum(1 for p in all_playlists if p.is_remix and p.deleted_at is None)
        remix_chains = {}
        max_generation = 0

        for playlist in all_playlists:
            if not playlist.is_remix or playlist.deleted_at:
                continue

            root_id = playlist.id
            current = playlist
            while current.parent_playlist:
                root_id = current.parent_playlist.id
                current = current.parent_playlist

            if root_id not in remix_chains:
                remix_chains[root_id] = 0

            remix_chains[root_id] += 1
            max_generation = max(max_generation, playlist.remix_generation)

        return {
            "total_remixes_created": total_remixes,
            "number_of_remix_chains": len(remix_chains),
            "max_remix_generation": max_generation,
            "average_remixes_per_original": (
                total_remixes / len(remix_chains) if remix_chains else 0
            ),
        }
