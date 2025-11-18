"""Artist discovery component for Spotify artist search and filtering."""

import asyncio
import structlog
from collections import Counter
from typing import Any, Dict, List, Optional, Set

from langchain_core.language_models.base import BaseLanguageModel

from ...utils.llm_response_parser import LLMResponseParser
from ...utils.config import config
from ...utils.artist_utils import ArtistDeduplicator
from ...utils.regional_filter import RegionalFilter
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

    def _should_filter_artist_by_region(
        self,
        artist_name: str,
        artist_genres: List[str],
        excluded_regions: List[str]
    ) -> tuple[bool, Optional[str]]:
        """Check if an artist should be filtered based on regional preferences.

        Args:
            artist_name: Name of the artist
            artist_genres: List of artist's genres
            excluded_regions: List of regions to exclude

        Returns:
            Tuple of (should_filter: bool, detected_region: Optional[str])
        """
        if not excluded_regions:
            return False, None

        artist_region = RegionalFilter.detect_artist_region(artist_name, artist_genres)
        if artist_region and RegionalFilter.is_region_excluded(artist_region, excluded_regions):
            return True, artist_region

        return False, artist_region

    def _get_popularity_sorted_artists(
        self,
        artists: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Sort artists by popularity and return top N.

        Args:
            artists: List of artists to sort
            limit: Maximum number of artists to return

        Returns:
            Top artists sorted by popularity
        """
        return sorted(
            artists,
            key=lambda x: x.get("popularity") or 0,
            reverse=True
        )[:limit]

    async def discover_mood_artists(self, state, mood_analysis: Dict[str, Any]) -> None:
        """Discover artists matching the mood using Spotify search and LLM filtering.

        This is the main entry point for artist discovery. It orchestrates:
        1. Collecting artists from multiple sources (LLM suggestions, genres, keywords)
        2. Filtering artists using heuristics and LLM validation
        3. Expanding the artist pool with genre-based discovery
        4. Validating expanded artists

        Args:
            state: Current agent state
            mood_analysis: Mood analysis results containing genre keywords, artist recommendations, etc.
        """
        try:
            logger.info("Starting artist discovery for mood")

            access_token = self._get_access_token(state)
            if not access_token:
                return

            # Phase 1: Collect candidate artists from multiple sources
            all_artists = await self._collect_candidate_artists(
                state, mood_analysis, access_token
            )
            if not all_artists:
                logger.warning("No artists found during discovery")
                return

            # Phase 2: Filter and validate artists
            filtered_artists, llm_filtered_ids = await self._filter_and_validate_artists(
                all_artists, state, mood_analysis
            )
            if not filtered_artists:
                logger.warning("No artists passed filtering")
                return

            # Phase 3: Expand and finalize artist pool
            await self._expand_and_finalize_artists(
                filtered_artists, llm_filtered_ids, state, mood_analysis, access_token
            )

        except Exception as e:
            logger.error(f"Error in artist discovery: {str(e)}", exc_info=True)
            # Don't fail the whole pipeline, just continue without artist discovery

    def _get_access_token(self, state) -> Optional[str]:
        """Extract and validate Spotify access token from state.

        Args:
            state: Current agent state

        Returns:
            Access token or None if not available
        """
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.warning("No Spotify access token available for artist discovery")
        return access_token

    async def _collect_candidate_artists(
        self,
        state,
        mood_analysis: Dict[str, Any],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Collect candidate artists from all available sources.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis results
            access_token: Spotify access token

        Returns:
            List of unique candidate artists
        """
        search_params = self._extract_search_parameters(state, mood_analysis)
        all_artists = await self._gather_artists_from_sources(search_params, access_token)

        unique_artists = ArtistDeduplicator.deduplicate(all_artists)
        logger.info(f"Found {len(unique_artists)} unique artists from search")

        return unique_artists

    def _extract_search_parameters(
        self,
        state,
        mood_analysis: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Extract search parameters from mood analysis.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis results

        Returns:
            Dictionary with genre_keywords, artist_recommendations, and search_keywords
        """
        genre_keywords = mood_analysis.get("genre_keywords", [])
        artist_recommendations = mood_analysis.get("artist_recommendations", [])
        search_keywords = mood_analysis.get("search_keywords", [])

        # Fallback to extracting keywords from prompt if none provided
        if not genre_keywords and not artist_recommendations and not search_keywords:
            search_keywords = self._text_processor.extract_search_keywords(state.mood_prompt)

        return {
            "genre_keywords": genre_keywords,
            "artist_recommendations": artist_recommendations,
            "search_keywords": search_keywords
        }

    async def _gather_artists_from_sources(
        self,
        search_params: Dict[str, List[str]],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Gather artists from all available sources.

        Args:
            search_params: Dictionary with search parameters
            access_token: Spotify access token

        Returns:
            Combined list of artists from all sources
        """
        all_artists = []

        # SOURCE 1: LLM-suggested artists (50% weight)
        llm_artists = await self._discover_from_llm_suggestions(
            search_params["artist_recommendations"], access_token
        )
        all_artists.extend(llm_artists)
        logger.info(f"Found {len(llm_artists)} artists from LLM suggestions")

        # SOURCE 2: Genre-based discovery (50% weight)
        genre_artists = await self._discover_from_genres(
            search_params["genre_keywords"], access_token
        )
        all_artists.extend(genre_artists)
        logger.info(f"Found {len(genre_artists)} artists from genre search")

        # SOURCE 3: Fallback keyword search if both sources failed
        if not all_artists and search_params["search_keywords"]:
            fallback_artists = await self._discover_from_keywords(
                search_params["search_keywords"], access_token
            )
            all_artists.extend(fallback_artists)

        return all_artists

    async def _discover_from_keywords(
        self,
        search_keywords: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Discover artists using general keyword search as fallback.

        Args:
            search_keywords: List of search keywords
            access_token: Spotify access token

        Returns:
            List of artists found via keyword search
        """
        artists = []
        for keyword in search_keywords[: config.fallback_search_keyword_limit]:
            try:
                keyword_artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=keyword,
                    limit=config.fallback_artist_search_limit
                )
                artists.extend(keyword_artists)
            except Exception as e:
                logger.error(f"Failed to search artists for keyword '{keyword}': {e}")

        logger.info(f"Found {len(artists)} artists from keyword fallback")
        return artists

    async def _filter_and_validate_artists(
        self,
        artists: List[Dict[str, Any]],
        state,
        mood_analysis: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Set[str]]:
        """Filter and validate artists using heuristics and LLM.

        Args:
            artists: List of candidate artists
            state: Current agent state
            mood_analysis: Mood analysis results

        Returns:
            Tuple of (filtered artists, set of LLM-filtered artist IDs)
        """
        # Step 1: Apply heuristic pruning to reduce cost
        pruned_artists = self._heuristic_prune_artists(artists, mood_analysis)
        logger.info(f"After heuristic pruning: {len(pruned_artists)} artists (from {len(artists)})")

        # Step 2: Apply LLM validation if available and needed
        llm_filtered_ids = set()
        if self.llm and len(pruned_artists) > config.llm_batch_validation_trigger:
            filtered_artists, llm_filtered_ids = await self._apply_llm_validation(
                pruned_artists, state, mood_analysis
            )
        else:
            # No LLM available - sort by popularity
            filtered_artists = self._get_popularity_sorted_artists(
                pruned_artists, config.artist_discovery_result_limit
            )

        # Step 3: Store discovered artists in state metadata
        self._store_discovered_artists(state, filtered_artists)

        return filtered_artists, llm_filtered_ids

    async def _apply_llm_validation(
        self,
        artists: List[Dict[str, Any]],
        state,
        mood_analysis: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Set[str]]:
        """Apply LLM batch validation to filter artists.

        Args:
            artists: List of artists to validate
            state: Current agent state
            mood_analysis: Mood analysis results

        Returns:
            Tuple of (validated artists, set of filtered artist IDs)
        """
        filtered_artists, llm_filtered_ids = await self._llm_batch_validate_artists(
            artists, state.mood_prompt, mood_analysis
        )
        logger.info(f"After LLM batch validation: {len(filtered_artists)} artists")

        # Fallback if LLM returns too few artists
        # Use heuristic fallback (popularity sort) for better performance instead of 2nd LLM call
        # Only do expensive 2nd LLM call if batch returned very few results (< 3)
        if len(filtered_artists) < config.llm_minimum_filtered_artists:
            if len(filtered_artists) < 3:
                logger.warning("LLM batch validation returned very few artists, trying alternative LLM filter")
                filtered_artists = await self._llm_filter_artists(
                    artists, state.mood_prompt, mood_analysis
                )
            else:
                logger.info(
                    f"LLM batch validation returned {len(filtered_artists)} artists "
                    f"(below target {config.llm_minimum_filtered_artists}), "
                    "using popularity-based fallback for better performance"
                )
                filtered_artists = self._get_popularity_sorted_artists(
                    artists, config.artist_discovery_result_limit
                )
            # Note: We keep the llm_filtered_ids from batch validation

        return filtered_artists, llm_filtered_ids

    def _store_discovered_artists(self, state, artists: List[Dict[str, Any]]) -> None:
        """Store discovered artists in state metadata.

        Args:
            state: Current agent state
            artists: List of filtered artists to store
        """
        state.metadata["discovered_artists"] = [
            {
                "id": artist.get("id"),
                "name": artist.get("name"),
                "genres": artist.get("genres", []),
                "popularity": artist.get("popularity", 50)
            }
            for artist in artists
        ]

    async def _expand_and_finalize_artists(
        self,
        filtered_artists: List[Dict[str, Any]],
        llm_filtered_ids: Set[str],
        state,
        mood_analysis: Dict[str, Any],
        access_token: str
    ) -> None:
        """Expand artist pool with genre-based discovery and finalize.

        Args:
            filtered_artists: Core filtered artists
            llm_filtered_ids: Set of artist IDs filtered by LLM
            state: Current agent state
            mood_analysis: Mood analysis results
            access_token: Spotify access token
        """
        core_artist_ids = [artist.get("id") for artist in filtered_artists]

        # Expand with genre-based discovery
        expanded_ids, expanded_details = await self._expand_with_genre_artists(
            core_artists=filtered_artists,
            access_token=access_token,
            existing_artist_ids=set(core_artist_ids),
            mood_analysis=mood_analysis,
            llm_filtered_artist_ids=llm_filtered_ids,
            state=state
        )

        # Validate expanded artists with LLM
        validated_expanded_ids = await self._validate_expanded_artists(
            expanded_details, expanded_ids, state, mood_analysis
        )

        # Combine and deduplicate
        all_artist_ids = core_artist_ids + validated_expanded_ids
        unique_artist_ids = list(dict.fromkeys(all_artist_ids))

        state.metadata["mood_matched_artists"] = unique_artist_ids

        logger.info(
            f"Discovered {len(filtered_artists)} core mood-matched artists + "
            f"{len(validated_expanded_ids)} validated genre-expanded artists = {len(unique_artist_ids)} total artists. "
            f"Top 5: {[a.get('name') for a in filtered_artists[:5]]}"
        )

    async def _validate_expanded_artists(
        self,
        expanded_details: List[Dict[str, Any]],
        expanded_ids: List[str],
        state,
        mood_analysis: Dict[str, Any]
    ) -> List[str]:
        """Validate expanded artists using LLM.

        Args:
            expanded_details: Full details of expanded artists
            expanded_ids: IDs of expanded artists
            state: Current agent state
            mood_analysis: Mood analysis results

        Returns:
            List of validated artist IDs
        """
        if not self.llm or not expanded_details:
            return expanded_ids

        logger.info(f"Running LLM batch validation on {len(expanded_details)} expanded artists")
        validated_artists, _ = await self._llm_batch_validate_artists(
            expanded_details, state.mood_prompt, mood_analysis
        )

        validated_ids = [a.get("id") for a in validated_artists if a.get("id")]
        logger.info(f"LLM validated {len(validated_ids)}/{len(expanded_details)} expanded artists")

        return validated_ids

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
            for i, artist in enumerate(artists[: config.artist_discovery_result_limit], 1):
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
                return self._get_popularity_sorted_artists(artists, config.artist_discovery_result_limit)

            logger.info(f"LLM selected {len(filtered_artists)} artists")
            return filtered_artists[: config.artist_discovery_result_limit]

        except Exception as e:
            logger.error(f"LLM artist filtering failed with unexpected error: {str(e)}")
            # Fallback to popularity-based selection
            return self._get_popularity_sorted_artists(artists, config.artist_discovery_result_limit)

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
        
        # Search for artists by name
        for artist_name in artist_recommendations[: config.artist_recommendation_limit]:
            try:
                logger.info(f"Searching for LLM-suggested artist: {artist_name}")
                artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=artist_name,
                    limit=config.artist_search_limit
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
                direct_artists = await self.spotify_service.search_artists_by_genre(
                    access_token=access_token,
                    genre=genre,
                    limit=config.genre_artist_search_limit
                )
                
                # Also search tracks for additional artist discovery
                track_artists = await self.spotify_service.search_tracks_for_artists(
                    access_token=access_token,
                    query=f"genre:{genre}",
                    limit=config.genre_track_search_limit
                )
                
                return direct_artists + track_artists
                
            except Exception as e:
                logger.error(f"Failed to search for genre '{genre}': {e}")
                return []
        
        # Process genres in parallel using configured limit
        genres_to_search = genre_keywords[: config.genre_anchor_search_limit]
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
    ) -> tuple[List[Dict[str, Any]], Set[str]]:
        """Use LLM to batch validate artists for cultural/genre relevance.

        This is more efficient than individual validation and allows the LLM
        to make better comparative decisions across all artists.

        Args:
            artists: List of artist candidates
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis results

        Returns:
            Tuple of (filtered list of validated artists, set of filtered artist IDs)
        """
        if not self.llm:
            return artists, set()

        try:
            # Process artists in batches
            all_validated = []
            filtered_artist_ids = set()
            batch_size = config.artist_batch_validation_size

            for i in range(0, len(artists), batch_size):
                batch = artists[i:i + batch_size]

                prompt = get_batch_artist_validation_prompt(batch, mood_prompt, mood_analysis)
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                result = LLMResponseParser.extract_json_from_response(response)

                keep_indices = result.get('keep_artists', [])
                filtered_info = result.get('filtered_artists', [])

                # Log filtered artists and track their IDs
                for filter_info in filtered_info:
                    artist_idx = filter_info.get('index', -1)
                    reason = filter_info.get('reason', '')
                    name = filter_info.get('name', 'Unknown')

                    # Track the filtered artist ID
                    if 0 <= artist_idx < len(batch):
                        artist_id = batch[artist_idx].get('id')
                        if artist_id:
                            filtered_artist_ids.add(artist_id)
                            logger.info(
                                f"LLM filtered artist '{name}' (ID: {artist_id}) - {reason}"
                            )
                        else:
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
                f"LLM batch validation: kept {len(all_validated)}/{len(artists)} artists, "
                f"filtered {len(filtered_artist_ids)} artist IDs"
            )

            return all_validated[: config.artist_discovery_result_limit], filtered_artist_ids

        except Exception as e:
            logger.error(f"LLM batch artist validation failed: {e}")
            # Fallback to returning all artists on error
            return artists, set()

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
            mood_analysis: Mood analysis containing genre keywords and regional preferences

        Returns:
            Pruned list of artists
        """
        if len(artists) <= config.heuristic_pruning_min_artists:
            # Not enough artists to warrant pruning
            return artists

        pruned = []
        genre_keywords = set(g.lower() for g in mood_analysis.get("genre_keywords", []))

        # Get regional preferences for filtering
        excluded_regions = mood_analysis.get("excluded_regions", [])

        for artist in artists:
            artist_name = artist.get('name', '')

            # Rule 1: Filter out artists with very low popularity (< 15)
            # These are likely obscure or have data quality issues
            popularity = artist.get("popularity")
            if popularity is None:
                popularity = 0
            if popularity < config.heuristic_min_artist_popularity:
                logger.debug(f"Filtered artist {artist_name} - low popularity: {popularity}")
                continue

            # Rule 2: Filter out artists with no genre information
            # These are likely incomplete/stale data
            artist_genres = artist.get("genres", [])
            if not artist_genres:
                logger.debug(f"Filtered artist {artist_name} - no genres")
                continue

            # Rule 3: Regional filtering - check if artist should be excluded based on region
            should_filter, artist_region = self._should_filter_artist_by_region(
                artist_name, artist_genres, excluded_regions
            )
            if should_filter:
                logger.info(
                    f"Filtered artist '{artist_name}' - region '{artist_region}' "
                    f"is in excluded regions: {excluded_regions}"
                )
                continue

            # Rule 4: If we have genre keywords from mood analysis, prioritize matches
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
        pruned = pruned[: config.heuristic_pruned_artist_limit]

        logger.info(
            f"Heuristic pruning: {len(artists)} → {len(pruned)} artists "
            f"(filtered {len(artists) - len(pruned)} low-quality/irrelevant)"
        )

        return pruned

    async def _expand_with_genre_artists(
        self,
        core_artists: List[Dict[str, Any]],
        access_token: str,
        existing_artist_ids: Optional[Set[str]] = None,
        mood_analysis: Optional[Dict[str, Any]] = None,
        llm_filtered_artist_ids: Optional[Set[str]] = None,
        state: Optional[Any] = None
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        """Expand artist pool with genre-based artist discovery for diversity.

        Alternative to deprecated get_related_artists endpoint.
        Searches for additional artists in the same genres as top mood-matched artists.

        Args:
            core_artists: Top mood-matched artists to expand from
            access_token: Spotify access token
            existing_artist_ids: Set of artist IDs to avoid duplicating
            mood_analysis: Mood analysis containing regional filtering preferences
            llm_filtered_artist_ids: Set of artist IDs that were filtered by LLM (to exclude)
            state: Agent state (optional, for LLM validation)

        Returns:
            Tuple of (list of expanded artist IDs, list of full artist details)
        """
        if not core_artists:
            return [], []

        expansion_config = self._prepare_expansion_config(
            core_artists, existing_artist_ids, llm_filtered_artist_ids, mood_analysis
        )

        if expansion_config["expansion_capacity"] == 0:
            logger.info("Skipping genre expansion – artist pool already at capacity")
            return [], []

        top_genres = self._extract_top_genres_from_artists(
            expansion_config["top_core_artists"],
            expansion_config["max_genres"]
        )

        if not top_genres:
            logger.warning("No genres found in core artists for expansion")
            return [], []

        logger.info(f"Expanding with genres: {top_genres[:3]}")

        expanded_artist_ids, expanded_artists_details, stats = await self._search_genre_based_artists(
            top_genres,
            access_token,
            expansion_config
        )

        logger.info(
            f"Added {len(expanded_artist_ids)} genre-based artists for diversity "
            f"(filtered {stats['llm_filtered_count']} LLM-rejected + {stats['regional_filtered_count']} regionally incompatible)"
        )
        return expanded_artist_ids, expanded_artists_details

    def _prepare_expansion_config(
        self,
        core_artists: List[Dict[str, Any]],
        existing_artist_ids: Optional[Set[str]],
        llm_filtered_artist_ids: Optional[Set[str]],
        mood_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare configuration for genre expansion.

        Args:
            core_artists: Core artists to expand from
            existing_artist_ids: Already discovered artist IDs
            llm_filtered_artist_ids: Artist IDs filtered by LLM
            mood_analysis: Mood analysis data

        Returns:
            Dictionary with expansion configuration
        """
        limits = config.limits
        core_limit = limits.genre_expansion_core_limit
        max_total_artists = config.artist_discovery_result_limit

        existing_artist_ids = set(existing_artist_ids or set())
        llm_filtered_artist_ids = set(llm_filtered_artist_ids or set())

        expansion_capacity = max(max_total_artists - len(existing_artist_ids), 0)
        expansion_target = min(limits.genre_expansion_target, expansion_capacity)
        excluded_regions = mood_analysis.get("excluded_regions", []) if mood_analysis else []

        return {
            "top_core_artists": core_artists[:core_limit],
            "expansion_capacity": expansion_capacity,
            "expansion_target": expansion_target,
            "search_limit": limits.genre_expansion_search_limit,
            "max_genres": limits.genre_expansion_max_genres,
            "min_popularity": limits.genre_expansion_min_popularity,
            "excluded_regions": excluded_regions,
            "existing_artist_ids": existing_artist_ids,
            "llm_filtered_artist_ids": llm_filtered_artist_ids,
        }

    def _extract_top_genres_from_artists(
        self,
        artists: List[Dict[str, Any]],
        max_genres: int
    ) -> List[str]:
        """Extract top genres from a list of artists, weighted by artist order.

        Args:
            artists: List of artists to extract genres from
            max_genres: Maximum number of genres to return

        Returns:
            List of top genre names
        """
        genre_counts = Counter()
        core_len = len(artists)

        for idx, artist in enumerate(artists):
            genres = artist.get("genres", [])
            if not genres:
                continue
            weight = core_len - idx  # Earlier artists carry more weight
            for genre in genres:
                genre_counts[genre] += weight

        return [genre for genre, _ in genre_counts.most_common(max_genres)]

    async def _search_genre_based_artists(
        self,
        genres: List[str],
        access_token: str,
        expansion_config: Dict[str, Any]
    ) -> tuple[List[str], List[Dict[str, Any]], Dict[str, int]]:
        """Search for artists in specified genres.

        Args:
            genres: List of genres to search
            access_token: Spotify access token
            expansion_config: Configuration for expansion

        Returns:
            Tuple of (expanded artist IDs, expanded artist details, filter stats)
        """
        expanded_artist_ids: List[str] = []
        expanded_artists_details: List[Dict[str, Any]] = []
        llm_filtered_count = 0
        regional_filtered_count = 0

        existing_artist_ids = expansion_config["existing_artist_ids"]
        llm_filtered_artist_ids = expansion_config["llm_filtered_artist_ids"]
        expansion_target = expansion_config["expansion_target"]
        search_limit = expansion_config["search_limit"]
        min_popularity = expansion_config["min_popularity"]
        excluded_regions = expansion_config["excluded_regions"]

        try:
            # Parallelize genre searches for better performance (50-60% speedup)
            async def search_genre(genre: str) -> List[Dict[str, Any]]:
                """Search for artists in a single genre."""
                try:
                    search_results = await self.spotify_service.search_spotify_artists(
                        access_token=access_token,
                        query=f'genre:"{genre}"',
                        limit=search_limit
                    )
                    return search_results if search_results else []
                except Exception as e:
                    logger.warning(f"Failed to search genre '{genre}': {e}")
                    return []

            # Execute all genre searches concurrently
            genre_search_results = await asyncio.gather(*[search_genre(g) for g in genres])

            # Process results from all genres
            for search_results in genre_search_results:
                if len(expanded_artist_ids) >= expansion_target:
                    break

                for artist in search_results:
                    if len(expanded_artist_ids) >= expansion_target:
                        break

                    should_add, filter_reason, filter_type = self._should_add_expanded_artist(
                        artist,
                        existing_artist_ids,
                        expanded_artist_ids,
                        llm_filtered_artist_ids,
                        min_popularity,
                        excluded_regions
                    )

                    if not should_add:
                        if filter_type == "llm":
                            llm_filtered_count += 1
                        elif filter_type == "regional":
                            regional_filtered_count += 1
                        continue

                    # Artist passed all filters
                    artist_id = artist.get("id")
                    expanded_artist_ids.append(artist_id)
                    expanded_artists_details.append(artist)
                    existing_artist_ids.add(artist_id)

        except Exception as e:
            logger.error(f"Error searching genre-based artists: {e}", exc_info=True)

        return expanded_artist_ids, expanded_artists_details, {
            "llm_filtered_count": llm_filtered_count,
            "regional_filtered_count": regional_filtered_count
        }

    def _should_add_expanded_artist(
        self,
        artist: Dict[str, Any],
        existing_artist_ids: Set[str],
        expanded_artist_ids: List[str],
        llm_filtered_artist_ids: Set[str],
        min_popularity: int,
        excluded_regions: List[str]
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Check if an artist should be added to the expanded pool.

        Args:
            artist: Artist dictionary
            existing_artist_ids: Set of existing artist IDs
            expanded_artist_ids: List of already expanded artist IDs
            llm_filtered_artist_ids: Set of LLM-filtered artist IDs
            min_popularity: Minimum popularity threshold
            excluded_regions: List of regions to exclude

        Returns:
            Tuple of (should_add: bool, reason: Optional[str], filter_type: Optional[str])
        """
        artist_id = artist.get("id")
        artist_name = artist.get("name", "")
        artist_genres = artist.get("genres", [])
        popularity = artist.get("popularity", 0)

        # Basic validation checks
        if (
            not artist_id
            or artist_id in existing_artist_ids
            or artist_id in expanded_artist_ids
            or popularity < min_popularity
        ):
            return False, None, None

        # Check if artist was previously filtered by LLM
        if artist_id in llm_filtered_artist_ids:
            logger.info(
                f"Skipping artist '{artist_name}' (ID: {artist_id}) - "
                f"was previously filtered by LLM batch validation"
            )
            return False, "LLM-filtered", "llm"

        # Apply regional filtering
        should_filter, artist_region = self._should_filter_artist_by_region(
            artist_name, artist_genres, excluded_regions
        )
        if should_filter:
            logger.info(
                f"Filtered expanded artist '{artist_name}' (ID: {artist_id}) - region '{artist_region}' "
                f"(genres: {artist_genres}) is in excluded regions: {excluded_regions}"
            )
            return False, f"Regional mismatch: {artist_region}", "regional"
        elif excluded_regions and artist_region:
            # Log artists that passed the filter for debugging
            logger.debug(
                f"Keeping expanded artist '{artist_name}' (ID: {artist_id}) - "
                f"detected region: {artist_region}, genres: {artist_genres}"
            )

        return True, None, None
