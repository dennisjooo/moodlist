"""Playlist creation service for creating and managing Spotify playlists."""

import logging
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...agents.states.agent_state import AgentState, RecommendationStatus
from ...agents.tools.spotify_service import SpotifyService
from .playlist_namer import PlaylistNamer
from .playlist_describer import PlaylistDescriber
from .track_adder import TrackAdder
from .playlist_validator import PlaylistValidator
from .playlist_summarizer import PlaylistSummarizer


logger = logging.getLogger(__name__)


class PlaylistCreationService:
    """Service for creating and managing Spotify playlists."""

    def __init__(
        self,
        spotify_service: SpotifyService,
        llm: Optional[BaseLanguageModel] = None,
        verbose: bool = False
    ):
        """Initialize the playlist creation service.

        Args:
            spotify_service: Service for Spotify API operations
            llm: Language model for playlist naming
            verbose: Whether to enable verbose logging
        """
        self.spotify_service = spotify_service
        self.verbose = verbose

        # Initialize component classes
        self.playlist_namer = PlaylistNamer(llm=llm)
        self.playlist_describer = PlaylistDescriber(llm=llm)
        self.track_adder = TrackAdder(spotify_service)
        self.playlist_validator = PlaylistValidator()
        self.playlist_summarizer = PlaylistSummarizer()

    async def create_playlist(self, state: AgentState) -> AgentState:
        """Execute playlist creation.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with playlist information
        """
        try:
            logger.info(f"Creating playlist for session {state.session_id}")

            # Check if we have recommendations to create playlist from
            if not state.recommendations:
                raise ValueError("No recommendations available for playlist creation")

            # Generate playlist name
            playlist_name = await self.playlist_namer.generate_name(state.mood_prompt, len(state.recommendations))

            # Generate playlist description
            playlist_description = await self.playlist_describer.generate_description(state.mood_prompt, len(state.recommendations))

            # Create playlist on Spotify
            access_token = state.metadata.get("spotify_access_token")
            if not access_token:
                raise ValueError("No Spotify access token available for playlist creation")

            playlist_data = await self.spotify_service.create_playlist(
                access_token=access_token,
                name=playlist_name,
                description=playlist_description,
                public=False
            )

            if not playlist_data:
                raise ValueError("Failed to create playlist on Spotify")

            # Update state with playlist information
            state.playlist_id = playlist_data["id"]
            state.playlist_name = playlist_name
            state.spotify_playlist_id = playlist_data["id"]
            state.current_step = "playlist_created"
            state.status = RecommendationStatus.CREATING_PLAYLIST

            # Add tracks to playlist
            await self.track_adder.add_tracks_to_playlist(state, playlist_data["id"])

            # Final state updates
            state.current_step = "completed"
            state.status = RecommendationStatus.COMPLETED

            # Store final metadata
            state.metadata["playlist_url"] = playlist_data.get("external_urls", {}).get("spotify")
            state.metadata["playlist_uri"] = playlist_data.get("uri")
            state.metadata["tracks_added"] = len(state.recommendations)
            state.metadata["playlist_creation_timestamp"] = state.updated_at.isoformat()

            logger.info(f"Successfully created playlist '{playlist_name}' with {len(state.recommendations)} tracks")

        except Exception as e:
            logger.error(f"Error in playlist creation: {str(e)}", exc_info=True)
            state.set_error(f"Playlist creation failed: {str(e)}")

        return state

    def get_playlist_summary(self, state: AgentState):
        """Get a summary of the created playlist.

        Args:
            state: Current agent state

        Returns:
            Playlist summary
        """
        return self.playlist_summarizer.get_playlist_summary(state)

    def validate_playlist_requirements(self, state: AgentState):
        """Validate that playlist creation requirements are met.

        Args:
            state: Current agent state

        Returns:
            List of validation errors (empty if valid)
        """
        return self.playlist_validator.validate_playlist_requirements(state)