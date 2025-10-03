"""Playlist creator agent for final playlist creation and management."""

import logging
import random
import re
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.spotify_service import SpotifyService


logger = logging.getLogger(__name__)


class PlaylistCreatorAgent(BaseAgent):
    """Agent for creating and managing Spotify playlists."""

    def __init__(
        self,
        spotify_service: SpotifyService,
        llm: Optional[BaseLanguageModel] = None,
        verbose: bool = False
    ):
        """Initialize the playlist creator agent.

        Args:
            spotify_service: Service for Spotify API operations
            llm: Language model for playlist naming
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="playlist_creator",
            description="Creates and manages Spotify playlists with recommended tracks",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service

    async def execute(self, state: AgentState) -> AgentState:
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
            playlist_name = await self._generate_playlist_name(state)

            # Generate playlist description
            playlist_description = self._generate_playlist_description(state)

            # Create playlist on Spotify
            access_token = state.metadata.get("spotify_access_token")
            if not access_token:
                raise ValueError("No Spotify access token available for playlist creation")

            playlist_data = await self.spotify_service.create_playlist(
                access_token=access_token,
                name=playlist_name,
                description=playlist_description,
                public=True
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
            await self._add_tracks_to_playlist(state, playlist_data["id"])

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

    async def _generate_playlist_name(self, state: AgentState) -> str:
        """Generate a creative playlist name based on mood.

        Args:
            state: Current agent state

        Returns:
            Generated playlist name
        """
        try:
            # Use LLM for creative playlist naming if available
            if self.llm:
                name = await self._generate_name_with_llm(state)
            else:
                name = self._generate_name_fallback(state)

            # Ensure name is not too long for Spotify (100 chars max)
            if len(name) > 100:
                name = name[:97] + "..."

            return name

        except Exception as e:
            logger.error(f"Error generating playlist name: {str(e)}")
            return self._generate_name_fallback(state)

    async def _generate_name_with_llm(self, state: AgentState) -> str:
        """Generate playlist name using LLM.

        Args:
            state: Current agent state

        Returns:
            LLM-generated playlist name
        """
        try:
            prompt = f"""
            Create a creative and appealing playlist name based on this mood description: "{state.mood_prompt}"

            The playlist contains {len(state.recommendations)} tracks that match this mood.

            Guidelines:
            - Keep it under 100 characters
            - Make it catchy and relevant to the mood
            - Avoid generic names like "My Playlist"
            - Consider the energy and emotion of the mood

            Return only the playlist name, nothing else.
            """

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            name = response.content.strip() if hasattr(response, 'content') else str(response).strip()

            # Clean up the name
            name = re.sub(r'^["\']|["\']$', '', name)  # Remove quotes
            name = re.sub(r'^Playlist:\s*', '', name, flags=re.IGNORECASE)  # Remove "Playlist:" prefix

            return name or self._generate_name_fallback(state)

        except Exception as e:
            logger.error(f"LLM name generation failed: {str(e)}")
            return self._generate_name_fallback(state)

    def _generate_name_fallback(self, state: AgentState) -> str:
        """Generate a fallback playlist name.

        Args:
            state: Current agent state

        Returns:
            Fallback playlist name
        """
        mood_prompt = state.mood_prompt.lower()

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
            if mood in mood_prompt:
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

    def _generate_playlist_description(self, state: AgentState) -> str:
        """Generate a descriptive playlist description using mood analysis.

        Args:
            state: Current agent state

        Returns:
            Generated playlist description
        """
        try:
            # Start with the original mood prompt
            description_parts = []
            
            # Use mood analysis if available
            if state.mood_analysis:
                mood_interpretation = state.mood_analysis.get("mood_interpretation")
                primary_emotion = state.mood_analysis.get("primary_emotion")
                energy_level = state.mood_analysis.get("energy_level")
                
                # Build a rich description
                if mood_interpretation:
                    description_parts.append(mood_interpretation)
                
                # Add emotion and energy if available
                emotion_energy_parts = []
                if primary_emotion:
                    emotion_energy_parts.append(primary_emotion)
                if energy_level:
                    emotion_energy_parts.append(energy_level)
            else:
                # Fallback to mood prompt if no analysis
                description_parts.append(f"Mood: {state.mood_prompt}")
            
            # Add track count
            track_count = len(state.recommendations)
            description_parts.append(f"{track_count} carefully selected tracks.")
            
            # Add branding
            description_parts.append("Created by MoodList.")
            
            # Join with proper spacing
            description = " ".join(description_parts)
            
            # Spotify description limit is 300 characters
            if len(description) > 300:
                description = description[:297] + "..."
            
            return description
            
        except Exception as e:
            logger.error(f"Error generating playlist description: {str(e)}")
            # Fallback to simple description
            return f"Mood-based playlist: {state.mood_prompt}. Created by MoodList."

    def _normalize_spotify_uri(self, uri_or_id: str) -> str:
        """Normalize track identifier to proper Spotify URI format.
        
        Args:
            uri_or_id: Track URI or ID
            
        Returns:
            Properly formatted Spotify URI
        """
        if not uri_or_id:
            return None
            
        # If already a proper URI, return as-is
        if uri_or_id.startswith('spotify:track:'):
            return uri_or_id
            
        # If it's a URI with different format, extract ID
        if 'spotify:' in uri_or_id:
            parts = uri_or_id.split(':')
            if len(parts) >= 3:
                return f"spotify:track:{parts[-1]}"
                
        # If it's just an ID, format it
        # Remove any URL prefixes if present
        track_id = uri_or_id.split('/')[-1].split('?')[0]
        return f"spotify:track:{track_id}"

    async def _add_tracks_to_playlist(self, state: AgentState, playlist_id: str):
        """Add recommended tracks to the Spotify playlist.

        Args:
            state: Current agent state
            playlist_id: Spotify playlist ID
        """
        try:
            if not state.recommendations:
                logger.warning("No recommendations to add to playlist")
                return

            # Extract and normalize Spotify URIs from recommendations
            track_uris = []
            for rec in state.recommendations:
                if rec.spotify_uri:
                    normalized_uri = self._normalize_spotify_uri(rec.spotify_uri)
                    if normalized_uri:
                        track_uris.append(normalized_uri)
                        logger.debug(f"Normalized URI: {rec.spotify_uri} -> {normalized_uri}")
                    else:
                        logger.warning(f"Could not normalize URI for track {rec.track_id}: {rec.spotify_uri}")
                elif rec.track_id:
                    # Try to use track_id as fallback
                    normalized_uri = self._normalize_spotify_uri(rec.track_id)
                    if normalized_uri:
                        track_uris.append(normalized_uri)
                        logger.debug(f"Using track_id as URI: {rec.track_id} -> {normalized_uri}")
                else:
                    logger.warning(f"No Spotify URI or track ID for recommendation")

            if not track_uris:
                logger.error("No valid Spotify URIs found in recommendations")
                return

            logger.info(f"Adding {len(track_uris)} tracks to playlist {playlist_id}")
            logger.debug(f"First 3 URIs: {track_uris[:3]}")

            # Split into chunks to respect API limits (100 tracks per request)
            chunk_size = 100
            for i in range(0, len(track_uris), chunk_size):
                chunk = track_uris[i:i + chunk_size]

                # Add tracks to playlist
                access_token = state.metadata.get("spotify_access_token")
                success = await self.spotify_service.add_tracks_to_playlist(
                    access_token=access_token,
                    playlist_id=playlist_id,
                    track_uris=chunk
                )

                if not success:
                    logger.error(f"Failed to add track chunk {i//chunk_size} to playlist")
                    continue

                # Add delay between chunks to respect rate limits
                import asyncio
                await asyncio.sleep(0.1)

            logger.info(f"Successfully added tracks to playlist {playlist_id}")

        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {str(e)}", exc_info=True)
            # Don't fail the entire process for track addition errors
            state.metadata["track_addition_error"] = str(e)

    def get_playlist_summary(self, state: AgentState) -> Dict[str, Any]:
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

    def validate_playlist_requirements(self, state: AgentState) -> List[str]:
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