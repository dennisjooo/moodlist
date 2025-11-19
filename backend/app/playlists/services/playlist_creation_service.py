"""Playlist creation service for creating and managing Spotify playlists."""

import asyncio
import structlog
from typing import Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...agents.states.agent_state import AgentState, RecommendationStatus
from ...agents.tools.spotify_service import SpotifyService
from ...core.exceptions import ValidationException, InternalServerError
from ...services.cover_image_generator import CoverImageGenerator
from .playlist_namer import PlaylistNamer
from .playlist_describer import PlaylistDescriber
from .track_adder import TrackAdder
from .playlist_validator import PlaylistValidator
from .playlist_summarizer import PlaylistSummarizer


logger = structlog.get_logger(__name__)


class PlaylistCreationService:
    """Service for creating and managing Spotify playlists."""

    def __init__(
        self,
        spotify_service: SpotifyService,
        llm: Optional[BaseLanguageModel] = None,
        verbose: bool = False,
        cover_style: str = "modern",
    ):
        """Initialize the playlist creation service.

        Args:
            spotify_service: Service for Spotify API operations
            llm: Language model for playlist naming
            verbose: Whether to enable verbose logging
            cover_style: Style for cover image generation (modern, diagonal, radial, mesh, waves, minimal)
        """
        self.spotify_service = spotify_service
        self.verbose = verbose
        self.cover_style = cover_style

        # Initialize component classes
        self.playlist_namer = PlaylistNamer(llm=llm)
        self.playlist_describer = PlaylistDescriber(llm=llm)
        self.track_adder = TrackAdder(spotify_service)
        self.playlist_validator = PlaylistValidator()
        self.playlist_summarizer = PlaylistSummarizer()
        self.cover_generator = CoverImageGenerator()

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
                raise ValidationException(
                    "No recommendations available for playlist creation"
                )

            # Generate playlist name and description in parallel (they don't depend on each other)
            playlist_name, playlist_description = await asyncio.gather(
                self.playlist_namer.generate_name(
                    state.mood_prompt, len(state.recommendations)
                ),
                self.playlist_describer.generate_description(
                    state.mood_prompt, len(state.recommendations)
                ),
            )

            # Create playlist on Spotify
            access_token = state.metadata.get("spotify_access_token")
            if not access_token:
                raise ValidationException(
                    "No Spotify access token available for playlist creation"
                )

            playlist_data = await self.spotify_service.create_playlist(
                access_token=access_token,
                name=playlist_name,
                description=playlist_description,
                public=False,
            )

            if not playlist_data:
                raise InternalServerError("Failed to create playlist on Spotify")

            # Update state with playlist information
            state.playlist_id = playlist_data["id"]
            state.playlist_name = playlist_name
            state.spotify_playlist_id = playlist_data["id"]
            state.current_step = "playlist_created"
            state.status = RecommendationStatus.CREATING_PLAYLIST

            # Add tracks to playlist
            await self.track_adder.add_tracks_to_playlist(state, playlist_data["id"])

            # Upload custom cover image if color scheme is available
            await self._upload_cover_image(state, playlist_data["id"], access_token)

            # Final state updates
            state.current_step = "completed"
            state.status = RecommendationStatus.COMPLETED

            # Store final metadata
            state.metadata["playlist_url"] = playlist_data.get("external_urls", {}).get(
                "spotify"
            )
            state.metadata["playlist_uri"] = playlist_data.get("uri")
            state.metadata["tracks_added"] = len(state.recommendations)
            state.metadata["playlist_creation_timestamp"] = state.updated_at.isoformat()

            logger.info(
                f"Successfully created playlist '{playlist_name}' with {len(state.recommendations)} tracks"
            )

        except Exception as e:
            logger.error(f"Error in playlist creation: {str(e)}", exc_info=True)
            state.set_error(f"Playlist creation failed: {str(e)}")

        return state

    async def _upload_cover_image(
        self, state: AgentState, playlist_id: str, access_token: str
    ) -> None:
        """Upload a custom cover image to the playlist based on mood colors.

        Args:
            state: Current agent state with mood analysis
            playlist_id: Spotify playlist ID
            access_token: Spotify access token
        """
        try:
            # Check if we have a color scheme in the mood analysis
            if not state.mood_analysis or "color_scheme" not in state.mood_analysis:
                logger.info(
                    "No color scheme available, skipping cover image generation"
                )
                return

            color_scheme = state.mood_analysis["color_scheme"]

            # Validate color scheme has all required colors
            if not all(
                key in color_scheme for key in ["primary", "secondary", "tertiary"]
            ):
                logger.warning(
                    "Incomplete color scheme, skipping cover image generation"
                )
                return

            logger.info(f"Generating cover image with colors: {color_scheme}")

            # Generate cover image as base64
            cover_base64 = self.cover_generator.generate_cover_base64(
                primary_color=color_scheme["primary"],
                secondary_color=color_scheme["secondary"],
                tertiary_color=color_scheme["tertiary"],
                style=self.cover_style,
            )

            # Upload to Spotify
            success = await self.spotify_service.upload_playlist_cover_image(
                access_token=access_token,
                playlist_id=playlist_id,
                image_base64=cover_base64,
            )

            if success:
                logger.info(
                    f"Successfully uploaded custom cover image to playlist {playlist_id}"
                )
                state.metadata["custom_cover_uploaded"] = True
                state.metadata["needs_cover_retry"] = False
            else:
                logger.warning(
                    f"Failed to upload custom cover image to playlist {playlist_id}"
                )
                state.metadata["custom_cover_uploaded"] = False
                state.metadata["needs_cover_retry"] = True
                # Store color scheme for retry during sync
                state.metadata["pending_cover_colors"] = {
                    "primary": color_scheme["primary"],
                    "secondary": color_scheme["secondary"],
                    "tertiary": color_scheme["tertiary"],
                    "style": self.cover_style,
                }

        except Exception as e:
            # Don't fail the entire playlist creation if cover upload fails
            logger.error(f"Error uploading cover image: {str(e)}", exc_info=True)
            state.metadata["custom_cover_uploaded"] = False
            state.metadata["needs_cover_retry"] = True
            state.metadata["cover_upload_error"] = str(e)
            # Store color scheme for retry during sync
            if "color_scheme" in state.mood_analysis:
                color_scheme = state.mood_analysis["color_scheme"]
                state.metadata["pending_cover_colors"] = {
                    "primary": color_scheme["primary"],
                    "secondary": color_scheme["secondary"],
                    "tertiary": color_scheme["tertiary"],
                    "style": self.cover_style,
                }

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
