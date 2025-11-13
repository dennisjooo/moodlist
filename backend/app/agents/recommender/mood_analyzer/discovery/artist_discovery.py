"""Artist discovery component for Spotify artist search and filtering."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ...utils.llm_response_parser import LLMResponseParser
from ...utils.config import config
from ...utils.artist_utils import ArtistDeduplicator
from ..prompts import (
    get_artist_filtering_prompt,
    get_batch_artist_validation_prompt,
)
from ..text import TextProcessor

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

            # Remove duplicates using shared utility
            unique_artists = ArtistDeduplicator.deduplicate(all_artists)

            logger.info(f"Found {len(unique_artists)} unique artists from search")

            # PHASE 3: Apply heuristic pruning BEFORE LLM to reduce cost and latency
            pruned_artists = self._heuristic_prune_artists(
                unique_artists, mood_analysis
            )
            logger.info(f"After heuristic pruning: {len(pruned_artists)} artists (from {len(unique_artists)})")

            # Use LLM to filter artists based on cultural/genre relevance
            if self.llm and len(pruned_artists) > 10:
                # Use batch LLM validation for efficiency and better context
                filtered_artists = await self._llm_batch_validate_artists(
                    pruned_artists, state.mood_prompt, mood_analysis
                )
                logger.info(f"After LLM batch validation: {len(filtered_artists)} artists")

                # If LLM returns too few, fall back to the original LLM filtering method
                if len(filtered_artists) < 5:
                    logger.warning("LLM batch validation returned too few artists, using fallback")
                    filtered_artists = await self._llm_filter_artists(
                        pruned_artists, state.mood_prompt, mood_analysis
                    )
            else:
                # Take more artists sorted by popularity for diversity
                # Mix of popular and less popular for variety
                filtered_artists = sorted(
                    pruned_artists,
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
        # Parse using centralized parser utility
        result = LLMResponseParser.extract_json_from_response(content, fallback={})
        
        if not result:
            logger.warning("Could not find JSON in LLM artist filtering response")
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
        
        Optimized: All genre searches run in parallel for better performance.
        
        Args:
            genre_keywords: List of genre keywords
            access_token: Spotify access token
            
        Returns:
            List of artist dictionaries
        """
        async def search_genre(genre: str) -> List[Dict[str, Any]]:
            """Search artists for a single genre."""
            try:
                logger.info(f"Searching artists for genre: {genre}")
                
                # Direct artist search by genre (NEW - primary method)
                # PERFORMANCE: Reduced from 40 to 20 artists per genre
                direct_artists = await self.spotify_service.search_artists_by_genre(
                    access_token=access_token,
                    genre=genre,
                    limit=20  # Reduced for performance
                )
                
                # Also search tracks for additional artist discovery
                # PERFORMANCE: Reduced from 30 to 15 tracks per genre
                track_artists = await self.spotify_service.search_tracks_for_artists(
                    access_token=access_token,
                    query=f"genre:{genre}",
                    limit=15  # Reduced for performance
                )
                
                return direct_artists + track_artists
                
            except Exception as e:
                logger.error(f"Failed to search for genre '{genre}': {e}")
                return []
        
        # Process up to 6 genres in parallel for performance
        genres_to_search = genre_keywords[:6]
        results = await asyncio.gather(
            *[search_genre(genre) for genre in genres_to_search],
            return_exceptions=True
        )
        
        # Flatten results and filter out exceptions
        genre_artists = []
        for result in results:
            if isinstance(result, list):
                genre_artists.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Exception in genre artist discovery: {result}")
        
        return genre_artists

    async def _llm_batch_validate_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to batch validate artists for cultural/genre relevance.

        This is more efficient than individual validation and allows the LLM
        to make better comparative decisions across all artists.

        Args:
            artists: List of artist candidates
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis results

        Returns:
            Filtered list of validated artists
        """
        if not self.llm:
            return artists
        
        try:
            # Process artists in batches
            all_validated = []
            batch_size = config.artist_batch_validation_size
            
            for i in range(0, len(artists), batch_size):
                batch = artists[i:i + batch_size]
                
                prompt = get_batch_artist_validation_prompt(batch, mood_prompt, mood_analysis)
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                result = LLMResponseParser.extract_json_from_response(response)
                
                keep_indices = result.get('keep_artists', [])
                filtered_info = result.get('filtered_artists', [])
                
                # Log filtered artists
                for filter_info in filtered_info:
                    artist_idx = filter_info.get('index', -1)
                    reason = filter_info.get('reason', '')
                    name = filter_info.get('name', 'Unknown')
                    logger.info(
                        "LLM filtered artist",
                        artist_index=artist_idx,
                        artist_name=name,
                        reason=reason,
                    )
                
                # Add kept artists to validated list
                for idx in keep_indices:
                    if 0 <= idx < len(batch):
                        all_validated.append(batch[idx])
                    else:
                        logger.warning(f"Invalid artist index from LLM: {idx}")
            
            logger.info(
                f"LLM batch validation: kept {len(all_validated)}/{len(artists)} artists"
            )
            
            return all_validated[:20]  # Return top 20 for diversity
        
        except Exception as e:
            logger.error(f"LLM batch artist validation failed: {e}")
            # Fallback to returning all artists on error
            return artists

    def _heuristic_prune_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply heuristic rules to prune artists BEFORE LLM filtering.

        Reduces the artist list using simple rules to minimize expensive LLM calls
        while preserving quality.

        Args:
            artists: List of candidate artists
            mood_analysis: Mood analysis containing genre keywords

        Returns:
            Pruned list of artists
        """
        if len(artists) <= 15:
            # Not enough artists to warrant pruning
            return artists

        pruned = []
        genre_keywords = set(g.lower() for g in mood_analysis.get("genre_keywords", []))

        for artist in artists:
            # Rule 1: Filter out artists with very low popularity (< 15)
            # These are likely obscure or have data quality issues
            popularity = artist.get("popularity")
            if popularity is None:
                popularity = 0
            if popularity < 15:
                logger.debug(f"Filtered artist {artist.get('name')} - low popularity: {popularity}")
                continue

            # Rule 2: Filter out artists with no genre information
            # These are likely incomplete/stale data
            artist_genres = artist.get("genres", [])
            if not artist_genres:
                logger.debug(f"Filtered artist {artist.get('name')} - no genres")
                continue

            # Rule 3: If we have genre keywords from mood analysis, prioritize matches
            # but don't exclude non-matches (keep for diversity)
            artist_genres_lower = set(g.lower() for g in artist_genres)
            has_genre_match = bool(genre_keywords & artist_genres_lower)

            # Add artist with metadata about genre match for prioritization
            artist_copy = artist.copy()
            artist_copy["_genre_match"] = has_genre_match
            pruned.append(artist_copy)

        # Sort by: genre match first, then popularity
        pruned.sort(key=lambda a: (a.get("_genre_match", False), a.get("popularity", 0)), reverse=True)

        # Remove the temporary _genre_match field
        for artist in pruned:
            artist.pop("_genre_match", None)

        # Take top 30 after heuristic pruning (down from potentially 50+)
        # This gives LLM a more manageable list while preserving variety
        pruned = pruned[:30]

        logger.info(
            f"Heuristic pruning: {len(artists)} → {len(pruned)} artists "
            f"(filtered {len(artists) - len(pruned)} low-quality/irrelevant)"
        )

        return pruned
