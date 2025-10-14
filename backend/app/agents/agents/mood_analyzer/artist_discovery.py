"""Artist discovery component for Spotify artist search and filtering."""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from .prompts import get_artist_filtering_prompt

logger = logging.getLogger(__name__)


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
                search_keywords = self._extract_search_keywords(state.mood_prompt)

            all_artists = []

            # 1. Search for artists by name (direct artist search) - EXPANDED
            for artist_name in artist_recommendations[:10]:  # Increased from 3 to 10 for more variety
                try:
                    logger.info(f"Searching for artist: {artist_name}")
                    artists = await self.spotify_service.search_spotify_artists(
                        access_token=access_token,
                        query=artist_name,
                        limit=3  # Keep at 3 per artist to avoid exact duplicates
                    )
                    all_artists.extend(artists)
                except Exception as e:
                    logger.error(f"Failed to search for artist '{artist_name}': {e}")

            # 2. Search tracks for genre keywords and extract artists - EXPANDED
            for genre in genre_keywords[:5]:  # Increased from 3 to 5 genres
                try:
                    logger.info(f"Searching tracks for genre: {genre}")
                    # Use genre filter format for better results
                    query = f"genre:{genre}"
                    artists = await self.spotify_service.search_tracks_for_artists(
                        access_token=access_token,
                        query=query,
                        limit=20  # Increased from 15 to 20 for more diverse artists
                    )
                    all_artists.extend(artists)
                except Exception as e:
                    logger.error(f"Failed to search tracks for genre '{genre}': {e}")

            # 3. Fallback: use general search keywords with artist search - EXPANDED
            if not all_artists and search_keywords:
                for keyword in search_keywords[:5]:  # Increased from 3 to 5
                    try:
                        artists = await self.spotify_service.search_spotify_artists(
                            access_token=access_token,
                            query=keyword,
                            limit=12  # Increased from 8 to 12
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
                    key=lambda x: x.get("popularity", 0),
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
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)

                selected_indices = result.get("selected_artist_indices", [])
                reasoning = result.get("reasoning", "")

                # Map indices to artists (1-indexed in prompt, 0-indexed in list)
                filtered_artists = [
                    artists[idx - 1] for idx in selected_indices
                    if 1 <= idx <= len(artists)
                ]

                # Store reasoning in state metadata
                if hasattr(self, '_current_state'):
                    self._current_state.metadata["artist_discovery_reasoning"] = reasoning

                logger.info(f"LLM selected {len(filtered_artists)} artists: {reasoning}")
                return filtered_artists[:20]  # Increased from 12 to 20 for max diversity

            else:
                logger.warning("Could not parse LLM artist filtering response")
                return artists[:20]  # Increased from 12 to 20

        except Exception as e:
            logger.error(f"LLM artist filtering failed: {str(e)}")
            # Fallback to popularity-based selection
            return sorted(artists, key=lambda x: x.get("popularity", 0), reverse=True)[:20]  # Increased from 12 to 20

    def _extract_search_keywords(self, mood_prompt: str) -> List[str]:
        """Extract search keywords from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            List of relevant search keywords
        """
        # Simple keyword extraction - can be enhanced with NLP
        keywords = []

        # Split by common delimiters
        words = mood_prompt.replace(",", " ").replace(" and ", " ").split()

        # Filter meaningful words (length > 3, not common stop words)
        stop_words = {"for", "with", "that", "this", "very", "some", "music", "songs", "playlist"}
        meaningful_words = [
            word.lower() for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]

        keywords.extend(meaningful_words)

        # Add some common mood-related terms
        mood_synonyms = {
            "chill": ["relaxed", "laid-back", "mellow"],
            "energetic": ["upbeat", "lively", "dynamic"],
            "sad": ["melancholy", "emotional", "bittersweet"],
            "happy": ["joyful", "cheerful", "uplifting"],
            "romantic": ["love", "intimate", "passionate"],
            "focus": ["concentration", "study", "instrumental"],
            "party": ["celebration", "fun", "dance"],
            "workout": ["fitness", "motivation", "pump"],
        }

        for word in meaningful_words:
            if word in mood_synonyms:
                keywords.extend(mood_synonyms[word])

        return list(set(keywords))  # Remove duplicates