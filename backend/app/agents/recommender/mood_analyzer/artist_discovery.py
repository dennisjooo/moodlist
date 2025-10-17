"""Artist discovery component for Spotify artist search and filtering."""

import json
import structlog
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from .prompts import get_artist_filtering_prompt
from .text_processor import TextProcessor

logger = structlog.get_logger(__name__)


class ArtistDiscovery:
    """Handles Spotify artist discovery and filtering for mood-based playlists."""

    def __init__(self, spotify_service=None, llm: Optional[BaseLanguageModel] = None):
        """Initialize the artist discovery component.

        Args:
            spotify_service: SpotifyService for artist discovery
            llm: Language model for artist filtering
        """
        self.spotify_service = spotify_service
        self.llm = llm
        self._text_processor = TextProcessor()

    async def discover_mood_artists(self, state, mood_analysis: Dict[str, Any]):
        """Discover artists matching the mood using Spotify search and LLM filtering.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis results
        """
        try:
            logger.info("Starting artist discovery for mood")

            # Get access token
            access_token = state.metadata.get("spotify_access_token")
            if not access_token:
                logger.warning("No Spotify access token available for artist discovery")
                return

            # Get genre keywords and artist recommendations from mood analysis
            genre_keywords = mood_analysis.get("genre_keywords", [])
            artist_recommendations = mood_analysis.get("artist_recommendations", [])

            # Fallback to search keywords if no specific genres/artists identified
            search_keywords = mood_analysis.get("search_keywords", [])
            if not genre_keywords and not artist_recommendations and not search_keywords:
                search_keywords = self._text_processor.extract_search_keywords(state.mood_prompt)

            all_artists = []

            # SOURCE 1: LLM-suggested artists (50% weight - reduced from dominant)
            llm_artists = await self._discover_from_llm_suggestions(
                artist_recommendations,
                access_token
            )
            all_artists.extend(llm_artists)
            logger.info(f"Found {len(llm_artists)} artists from LLM suggestions")

            # SOURCE 2: Genre-based discovery (50% weight - increased from secondary)
            genre_artists = await self._discover_from_genres(
                genre_keywords,
                access_token
            )
            all_artists.extend(genre_artists)
            logger.info(f"Found {len(genre_artists)} artists from genre search")

            # Fallback: use general search keywords if both sources failed
            if not all_artists and search_keywords:
                for keyword in search_keywords[:5]:
                    try:
                        artists = await self.spotify_service.search_spotify_artists(
                            access_token=access_token,
                            query=keyword,
                            limit=12
                        )
                        all_artists.extend(artists)
                    except Exception as e:
                        logger.error(f"Failed to search artists for keyword '{keyword}': {e}")

            if not all_artists:
                logger.warning("No artists found during discovery")
                return

            # Remove duplicates
            seen_ids = set()
            unique_artists = []
            for artist in all_artists:
                artist_id = artist.get("id")
                if artist_id and artist_id not in seen_ids:
                    seen_ids.add(artist_id)
                    unique_artists.append(artist)

            logger.info(f"Found {len(unique_artists)} unique artists from search")

            # Use LLM to filter artists if available - EXPANDED for diversity
            if self.llm and len(unique_artists) > 10:
                filtered_artists = await self._llm_filter_artists(
                    unique_artists, state.mood_prompt, mood_analysis
                )
            else:
                # Take more artists sorted by popularity for diversity
                # Mix of popular and less popular for variety
                filtered_artists = sorted(
                    unique_artists,
                    key=lambda x: x.get("popularity") or 0,
                    reverse=True
                )[:20]  # Increased from 8 to 20 for maximum diversity

            # Store in state metadata
            state.metadata["discovered_artists"] = [
                {
                    "id": artist.get("id"),
                    "name": artist.get("name"),
                    "genres": artist.get("genres", []),
                    "popularity": artist.get("popularity", 50)
                }
                for artist in filtered_artists
            ]
            state.metadata["mood_matched_artists"] = [artist.get("id") for artist in filtered_artists]

            logger.info(f"Discovered {len(filtered_artists)} mood-matched artists: {[a.get('name') for a in filtered_artists[:5]]}")

        except Exception as e:
            logger.error(f"Error in artist discovery: {str(e)}", exc_info=True)
            # Don't fail the whole pipeline, just continue without artist discovery

    async def _llm_filter_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to filter and select artists that best match the mood.

        Args:
            artists: List of artist candidates
            mood_prompt: User's mood description
            mood_analysis: Mood analysis results

        Returns:
            Filtered list of artists (8-12 artists)
        """
        try:
            # Prepare artist summary for LLM
            artists_summary = []
            for i, artist in enumerate(artists[:20], 1):  # Limit to 20 for LLM context
                genres_str = ", ".join(artist.get("genres", [])[:3]) or "no genres listed"
                artists_summary.append(
                    f"{i}. {artist.get('name')} - Genres: {genres_str}, Popularity: {artist.get('popularity', 50)}"
                )

            mood_interpretation = mood_analysis.get("mood_interpretation", mood_prompt)

            prompt = get_artist_filtering_prompt(mood_prompt, mood_interpretation, chr(10).join(artists_summary))

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse JSON response
            filtered_artists = self._parse_llm_artist_response(content, artists)
            
            if not filtered_artists:
                logger.warning("No valid artists selected by LLM, falling back to popularity-based selection")
                return sorted(artists, key=lambda x: x.get("popularity") or 0, reverse=True)[:20]
            
            logger.info(f"LLM selected {len(filtered_artists)} artists")
            return filtered_artists[:20]  # Increased from 12 to 20 for max diversity

        except Exception as e:
            logger.error(f"LLM artist filtering failed with unexpected error: {str(e)}")
            # Fallback to popularity-based selection
            return sorted(artists, key=lambda x: x.get("popularity") or 0, reverse=True)[:20]  # Increased from 12 to 20

    def _parse_llm_artist_response(
        self,
        content: str,
        artists: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse LLM response and extract selected artists.

        Args:
            content: Raw LLM response content
            artists: Original list of artist candidates

        Returns:
            List of selected artists, or empty list if parsing fails
        """
        # Find JSON in response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1

        if json_start < 0 or json_end <= json_start:
            logger.warning("Could not find JSON in LLM artist filtering response")
            logger.debug(f"Raw LLM response: {content[:500]}")
            return []

        json_str = content[json_start:json_end]
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {str(e)}")
            logger.debug(f"Raw LLM response: {content[:500]}")
            return []
        
        # Extract and validate selected indices
        selected_indices = result.get("selected_artist_indices", [])
        reasoning = result.get("reasoning", "")
        
        if not isinstance(selected_indices, list):
            logger.warning(f"selected_artist_indices is not a list: {type(selected_indices)}")
            return []
        
        # Map indices to artists (1-indexed in prompt, 0-indexed in list)
        filtered_artists = []
        for idx in selected_indices:
            if isinstance(idx, int) and 1 <= idx <= len(artists):
                filtered_artists.append(artists[idx - 1])
            else:
                logger.warning(f"Invalid artist index: {idx}")
        
        if not filtered_artists:
            logger.warning("No valid artists selected by LLM")
            return []
        
        # Store reasoning in state metadata
        if hasattr(self, '_current_state'):
            self._current_state.metadata["artist_discovery_reasoning"] = reasoning
        
        logger.info(f"LLM artist selection reasoning: {reasoning}")
        return filtered_artists

    async def _discover_from_llm_suggestions(
        self,
        artist_recommendations: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Discover artists from LLM-suggested artist names.
        
        Args:
            artist_recommendations: List of artist names suggested by LLM
            access_token: Spotify access token
            
        Returns:
            List of artist dictionaries
        """
        llm_artists = []
        
        # Search for artists by name (reduced from 10 to 8 for 50% weight)
        for artist_name in artist_recommendations[:8]:
            try:
                logger.info(f"Searching for LLM-suggested artist: {artist_name}")
                artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=artist_name,
                    limit=3  # Keep at 3 per artist to avoid exact duplicates
                )
                llm_artists.extend(artists)
            except Exception as e:
                logger.error(f"Failed to search for artist '{artist_name}': {e}")
        
        return llm_artists

    async def _discover_from_genres(
        self,
        genre_keywords: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Discover artists directly from genres (enhanced for 50% weight).
        
        Args:
            genre_keywords: List of genre keywords
            access_token: Spotify access token
            
        Returns:
            List of artist dictionaries
        """
        genre_artists = []
        
        # Process up to 10 genres (expanded from 5)
        for genre in genre_keywords[:10]:
            try:
                logger.info(f"Searching artists for genre: {genre}")
                
                # Direct artist search by genre (NEW - primary method)
                direct_artists = await self.spotify_service.search_artists_by_genre(
                    access_token=access_token,
                    genre=genre,
                    limit=40  # Get more artists per genre
                )
                genre_artists.extend(direct_artists)
                
                # Also search tracks for additional artist discovery
                track_artists = await self.spotify_service.search_tracks_for_artists(
                    access_token=access_token,
                    query=f"genre:{genre}",
                    limit=30  # Increased from 20
                )
                genre_artists.extend(track_artists)
                
            except Exception as e:
                logger.error(f"Failed to search for genre '{genre}': {e}")
                continue
        
        return genre_artists
