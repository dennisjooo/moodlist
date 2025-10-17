"""RecoBeat API service that coordinates all RecoBeat tools."""

import asyncio
import hashlib
import structlog
from typing import Dict, List, Optional, Any

from .agent_tools import AgentTools
from .reccobeat.track_recommendations import TrackRecommendationsTool
from .reccobeat.track_info import GetMultipleTracksTool, GetTrackAudioFeaturesTool
from .reccobeat.artist_info import SearchArtistTool, GetMultipleArtistsTool, GetArtistTracksTool
from ..core.cache import cache_manager


logger = structlog.get_logger(__name__)


class RecoBeatService:
    """Service for coordinating RecoBeat API operations."""

    def __init__(self):
        """Initialize the RecoBeat service."""
        self.tools = AgentTools()

        # Register all RecoBeat tools
        self._register_tools()

        logger.info("Initialized RecoBeat service with all tools")

    def _make_cache_key(self, operation: str, *args) -> str:
        """Create a cache key for RecoBeat operations.

        Args:
            operation: Type of operation (e.g., 'track_recommendations', 'track_info')
            *args: Operation parameters

        Returns:
            Cache key string
        """
        # Create deterministic key from operation and parameters
        key_components = [operation] + [str(arg) for arg in args]
        key_string = ":".join(key_components)

        # Hash for consistent length and security
        return hashlib.md5(key_string.encode()).hexdigest()

    async def _get_cached_recommendations(
        self,
        seeds: List[str],
        size: int,
        mood_features: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached track recommendations if available.

        Args:
            seeds: List of track IDs used as seeds
            size: Number of recommendations requested
            mood_features: Optional mood-based audio features
            **kwargs: Additional parameters

        Returns:
            Cached recommendations or None if not available/expired
        """
        # Create cache key from parameters
        cache_params = [str(seeds), str(size)]
        if mood_features:
            # Sort mood features for consistent key generation
            sorted_features = sorted(mood_features.items())
            cache_params.append(str(sorted_features))
        cache_params.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])

        cache_key = self._make_cache_key("track_recommendations", *cache_params)

        # Try to get from cache (15 minute TTL for recommendations)
        cached_result = await cache_manager.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for track recommendations (key: {cache_key[:8]}...)")
            return cached_result.get("recommendations", [])

        return None

    async def _cache_recommendations(
        self,
        seeds: List[str],
        size: int,
        recommendations: List[Dict[str, Any]],
        mood_features: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> None:
        """Cache track recommendations for future use.

        Args:
            seeds: List of track IDs used as seeds
            size: Number of recommendations requested
            recommendations: Recommendations to cache
            mood_features: Optional mood-based audio features
            **kwargs: Additional parameters
        """
        # Create cache key from parameters
        cache_params = [str(seeds), str(size)]
        if mood_features:
            sorted_features = sorted(mood_features.items())
            cache_params.append(str(sorted_features))
        cache_params.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])

        cache_key = self._make_cache_key("track_recommendations", *cache_params)

        # Cache with 15 minute TTL
        cache_data = {
            "recommendations": recommendations,
            "cached_at": asyncio.get_event_loop().time(),
            "parameters": {
                "seeds": seeds,
                "size": size,
                "mood_features": mood_features,
                "kwargs": kwargs
            }
        }

        await cache_manager.cache.set(cache_key, cache_data, ttl=1800)  # 30 minutes
        logger.debug(f"Cached track recommendations (key: {cache_key[:8]}...)")

    def _register_tools(self):
        """Register all RecoBeat tools."""
        tools_to_register = [
            TrackRecommendationsTool(),
            GetMultipleTracksTool(),
            GetTrackAudioFeaturesTool(),
            SearchArtistTool(),
            GetMultipleArtistsTool(),
            GetArtistTracksTool()
        ]

        for tool in tools_to_register:
            self.tools.register_tool(tool)

    async def get_track_recommendations(
        self,
        seeds: List[str],
        size: int = 20,
        mood_features: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Get track recommendations with mood-based features.

        Args:
            seeds: List of track IDs to use as seeds
            size: Number of recommendations to return
            mood_features: Optional mood-based audio features
            **kwargs: Additional parameters for the API

        Returns:
            List of track recommendations
        """
        # Try to get from cache first
        cached_recommendations = await self._get_cached_recommendations(
            seeds, size, mood_features, **kwargs
        )

        if cached_recommendations:
            logger.info(f"Returning {len(cached_recommendations)} cached recommendations")
            return cached_recommendations

        # Cache miss - fetch from API
        logger.info(f"Cache miss for recommendations, fetching from API")

        tool = self.tools.get_tool("get_track_recommendations")
        if not tool:
            raise ValueError("Track recommendations tool not available")

        # Merge mood features with kwargs
        if mood_features:
            api_params = {**mood_features, **kwargs}
        else:
            api_params = kwargs

        result = await tool._run(seeds=seeds, size=size, **api_params)

        if not result.success:
            logger.error(f"Failed to get recommendations: {result.error}")
            return []

        recommendations = result.data.get("recommendations", [])

        # Cache the successful result
        await self._cache_recommendations(
            seeds, size, recommendations, mood_features, **kwargs
        )

        logger.info(f"Fetched and cached {len(recommendations)} fresh recommendations")
        return recommendations

    async def convert_spotify_tracks_to_reccobeat(
        self,
        spotify_track_ids: List[str]
    ) -> Dict[str, str]:
        """Convert Spotify track IDs to RecoBeat IDs using batch lookup with parallel processing.

        Args:
            spotify_track_ids: List of Spotify track IDs

        Returns:
            Dictionary mapping Spotify ID to RecoBeat ID
        """
        if not spotify_track_ids:
            return {}

        id_mapping = {}

        # Get multiple tracks tool
        tracks_tool = self.tools.get_tool("get_multiple_tracks")
        if not tracks_tool:
            logger.warning("Multiple tracks tool not available for ID conversion")
            return {}

        # Process in chunks of 40 (API limit) with parallel processing
        chunk_size = 40
        chunks = [spotify_track_ids[i:i + chunk_size] for i in range(0, len(spotify_track_ids), chunk_size)]

        # Process chunks in parallel (limit concurrency to avoid overwhelming the API)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent chunk requests

        async def process_chunk(chunk: List[str]) -> Dict[str, str]:
            """Process a single chunk of track IDs."""
            async with semaphore:
                try:
                    result = await tracks_tool._run(ids=chunk)

                    if result.success:
                        tracks = result.data.get("tracks", [])
                        chunk_mapping = {}

                        for track in tracks:
                            reccobeat_id = track.get("id")
                            spotify_uri = track.get("spotify_uri", "")

                            # Extract Spotify ID from URI
                            if spotify_uri and "spotify:track:" in spotify_uri:
                                spotify_id = spotify_uri.replace("spotify:track:", "")
                            elif "/" in spotify_uri:
                                spotify_id = spotify_uri.split("/")[-1]
                            else:
                                # Assume the input ID matches
                                for orig_id in chunk:
                                    if orig_id not in chunk_mapping:
                                        spotify_id = orig_id
                                        break

                            if reccobeat_id:
                                chunk_mapping[spotify_id] = reccobeat_id

                        return chunk_mapping

                except Exception as e:
                    logger.debug(f"Error converting track IDs chunk: {e}")

                return {}

        # Execute all chunks in parallel
        try:
            chunk_results = await asyncio.gather(*[process_chunk(chunk) for chunk in chunks])

            # Combine results from all chunks
            for chunk_result in chunk_results:
                id_mapping.update(chunk_result)

        except Exception as e:
            logger.error(f"Error in parallel track ID conversion: {e}")

        logger.info(f"Converted {len(id_mapping)}/{len(spotify_track_ids)} Spotify track IDs to RecoBeat IDs")
        return id_mapping

    async def get_tracks_audio_features(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get audio features for multiple tracks with parallel processing.

        Args:
            track_ids: List of Spotify or RecoBeat track IDs

        Returns:
            Dictionary mapping original track IDs to their audio features
        """
        features_map = {}

        # Get audio features tool
        features_tool = self.tools.get_tool("get_track_audio_features")
        if not features_tool:
            logger.warning("Audio features tool not available")
            return features_map

        # Try to convert Spotify IDs to RecoBeat IDs first (already batched and parallel)
        id_mapping = await self.convert_spotify_tracks_to_reccobeat(track_ids)
        logger.info(f"Successfully converted {len(id_mapping)}/{len(track_ids)} Spotify tracks to RecoBeat IDs")

        # First pass: check cache for all tracks
        tracks_needing_fetch = []
        for track_id in track_ids:
            # Skip if we couldn't convert the Spotify ID to RecoBeat ID
            if track_id not in id_mapping:
                logger.debug(f"Skipping track {track_id} - not found in RecoBeat database")
                continue

            reccobeat_id = id_mapping[track_id]

            # Try cache first for individual track features
            cache_key = self._make_cache_key("track_audio_features", reccobeat_id)
            cached_features = await cache_manager.cache.get(cache_key)

            if cached_features:
                logger.debug(f"Cache hit for audio features of track {reccobeat_id}")
                features_map[track_id] = cached_features
            else:
                tracks_needing_fetch.append((track_id, reccobeat_id))

        # If all tracks were cached, return early
        if not tracks_needing_fetch:
            logger.info(f"All {len(track_ids)} tracks found in cache")
            return features_map

        logger.info(f"Fetching audio features for {len(tracks_needing_fetch)} tracks in parallel (cached: {len(features_map)})")

        # Parallel fetch with concurrency limit
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

        async def fetch_single_track_features(track_id: str, reccobeat_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
            """Fetch audio features for a single track."""
            async with semaphore:
                try:
                    result = await features_tool._run(track_id=reccobeat_id)
                    if result.success:
                        # Cache individual track features for 1 hour
                        cache_key = self._make_cache_key("track_audio_features", reccobeat_id)
                        await cache_manager.cache.set(cache_key, result.data, ttl=3600)
                        logger.debug(f"Cached audio features for track {reccobeat_id}")
                        return track_id, result.data
                    else:
                        # 404 errors are common - track might not exist in RecoBeat
                        if "404" in str(result.error):
                            logger.debug(f"Track {reccobeat_id} not found in RecoBeat (404)")
                        else:
                            logger.warning(f"Failed to get features for track {reccobeat_id}: {result.error}")
                        return track_id, None
                except Exception as e:
                    # 404 errors are expected for many Spotify tracks
                    if "404" in str(e):
                        logger.debug(f"Track {reccobeat_id} not found in RecoBeat: {e}")
                    else:
                        logger.error(f"Error getting features for track {reccobeat_id}: {e}")
                    return track_id, None

        # Execute all fetches in parallel
        try:
            results = await asyncio.gather(*[
                fetch_single_track_features(track_id, reccobeat_id)
                for track_id, reccobeat_id in tracks_needing_fetch
            ])

            # Combine results
            for track_id, features in results:
                if features:
                    features_map[track_id] = features

            logger.info(f"Successfully fetched {len([f for _, f in results if f])}/{len(tracks_needing_fetch)} audio features in parallel")

        except Exception as e:
            logger.error(f"Error in parallel audio features fetching: {e}")

        return features_map

    async def search_artists_by_mood(self, mood_keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for artists that match mood keywords.

        Args:
            mood_keywords: List of mood-related keywords
            limit: Maximum number of artists to return

        Returns:
            List of matching artists
        """
        search_tool = self.tools.get_tool("search_artists")
        if not search_tool:
            logger.warning("Artist search tool not available")
            return []

        all_artists = []

        # Search for each mood keyword
        for keyword in mood_keywords:
            try:
                result = await search_tool._run(
                    search_text=keyword,
                    size=min(limit, 25)  # RecoBeat max per page
                )

                if result.success:
                    artists = result.data.get("artists", [])
                    all_artists.extend(artists)

                    # Break if we have enough artists
                    if len(all_artists) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error searching for artists with keyword '{keyword}': {e}")

        # Remove duplicates and limit results
        seen_ids = set()
        unique_artists = []
        for artist in all_artists:
            artist_id = artist.get("id")
            if artist_id and artist_id not in seen_ids:
                seen_ids.add(artist_id)
                unique_artists.append(artist)
                if len(unique_artists) >= limit:
                    break

        return unique_artists

    async def get_tracks_by_ids(self, track_ids: List[str]) -> List[Dict[str, Any]]:
        """Get track information for multiple track IDs with parallel processing and caching.

        Args:
            track_ids: List of track IDs

        Returns:
            List of track information
        """
        if not track_ids:
            return []

        # Try to get from cache first (30 min TTL for track lookups)
        cache_key = self._make_cache_key("tracks_by_ids", str(sorted(track_ids)))
        cached_result = await cache_manager.cache.get(cache_key)

        if cached_result:
            logger.info(f"Cache hit for track lookup (key: {cache_key[:8]}...)")
            return cached_result.get("tracks", [])

        # Split into chunks to respect API limits (40 per request)
        chunk_size = 40
        chunks = [track_ids[i:i + chunk_size] for i in range(0, len(track_ids), chunk_size)]

        tracks_tool = self.tools.get_tool("get_multiple_tracks")
        if not tracks_tool:
            logger.warning("Multiple tracks tool not available")
            return []

        # Process chunks in parallel with concurrency limit
        semaphore = asyncio.Semaphore(8)  # Max 8 concurrent chunk requests

        async def process_track_chunk(chunk: List[str]) -> List[Dict[str, Any]]:
            """Process a single chunk of track IDs."""
            async with semaphore:
                try:
                    result = await tracks_tool._run(ids=chunk)
                    if result.success:
                        tracks = result.data.get("tracks", [])
                        return tracks
                    else:
                        logger.warning(f"Failed to get tracks for chunk: {result.error}")
                        return []

                except Exception as e:
                    logger.error(f"Error getting tracks for chunk: {e}")
                    return []

        # Execute all chunks in parallel
        try:
            chunk_results = await asyncio.gather(*[process_track_chunk(chunk) for chunk in chunks])

            # Combine results from all chunks
            all_tracks = []
            for chunk_result in chunk_results:
                all_tracks.extend(chunk_result)

        except Exception as e:
            logger.error(f"Error in parallel track fetching: {e}")
            all_tracks = []

        # Cache the successful result for 30 minutes
        if all_tracks:
            cache_data = {
                "tracks": all_tracks,
                "cached_at": asyncio.get_event_loop().time(),
                "track_ids": track_ids
            }
            await cache_manager.cache.set(cache_key, cache_data, ttl=1800)  # 30 minutes
            logger.debug(f"Cached track lookup result (key: {cache_key[:8]}...)")

        return all_tracks

    async def convert_spotify_artist_to_reccobeat(
        self,
        spotify_artist_ids: List[str]
    ) -> Dict[str, str]:
        """Convert Spotify artist IDs to RecoBeat IDs using batch lookup.

        Args:
            spotify_artist_ids: List of Spotify artist IDs

        Returns:
            Dictionary mapping Spotify ID to RecoBeat ID
        """
        if not spotify_artist_ids:
            return {}
        
        id_mapping = {}
        
        # Get multiple artists tool
        artists_tool = self.tools.get_tool("get_multiple_artists")
        if not artists_tool:
            logger.warning("Multiple artists tool not available for ID conversion")
            return {}
        
        # Process in chunks of 40 (API limit)
        for i in range(0, len(spotify_artist_ids), 40):
            chunk = spotify_artist_ids[i:i + 40]
            
            try:
                result = await artists_tool._run(ids=chunk)
                
                if result.success:
                    artists = result.data.get("artists", [])
                    for artist in artists:
                        reccobeat_id = artist.get("id")
                        spotify_uri = artist.get("href", "")
                        
                        # Extract Spotify ID from URI or href
                        if spotify_uri and "spotify:artist:" in spotify_uri:
                            spotify_id = spotify_uri.replace("spotify:artist:", "")
                        elif "/" in spotify_uri:
                            spotify_id = spotify_uri.split("/")[-1]
                        else:
                            # Assume the input ID matches
                            for orig_id in chunk:
                                if orig_id not in id_mapping:
                                    spotify_id = orig_id
                                    break
                        
                        if reccobeat_id:
                            id_mapping[spotify_id] = reccobeat_id
                            
            except Exception as e:
                logger.debug(f"Error converting artist IDs chunk: {e}")
                continue
        
        logger.info(f"Converted {len(id_mapping)}/{len(spotify_artist_ids)} Spotify artist IDs to RecoBeat IDs")
        return id_mapping

    async def get_artist_tracks(
        self,
        artist_id: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get tracks from a specific artist.

        Args:
            artist_id: Spotify or RecoBeat artist ID (will attempt conversion)
            limit: Maximum number of tracks to return

        Returns:
            List of tracks from the artist
        """
        artist_tracks_tool = self.tools.get_tool("get_artist_tracks")
        if not artist_tracks_tool:
            logger.warning("Artist tracks tool not available")
            return []

        # Try to convert Spotify ID to RecoBeat ID first
        id_mapping = await self.convert_spotify_artist_to_reccobeat([artist_id])
        
        # Skip if artist not in RecoBeat database
        if artist_id not in id_mapping:
            logger.debug(f"Artist {artist_id} not found in RecoBeat database - skipping")
            return []
        
        reccobeat_artist_id = id_mapping[artist_id]
        logger.debug(f"Converted Spotify artist {artist_id} to RecoBeat ID {reccobeat_artist_id}")

        try:
            result = await artist_tracks_tool._run(
                artist_id=reccobeat_artist_id,
                page=0,
                size=min(limit, 50)
            )

            if result.success:
                return result.data.get("tracks", [])
            else:
                # 404 errors are common - artist might not exist in RecoBeat
                if "404" in str(result.error):
                    logger.debug(f"Artist {reccobeat_artist_id} not found in RecoBeat (404)")
                else:
                    logger.warning(f"Failed to get tracks for artist {reccobeat_artist_id}: {result.error}")
                return []

        except Exception as e:
            # 404 errors are expected for many artists
            if "404" in str(e):
                logger.debug(f"Artist {reccobeat_artist_id} not found in RecoBeat: {e}")
            else:
                logger.error(f"Error getting tracks for artist {reccobeat_artist_id}: {e}")
            return []

    def get_available_tools(self) -> List[str]:
        """Get list of available RecoBeat tools.

        Returns:
            List of tool names
        """
        return [
            "get_track_recommendations",
            "get_multiple_tracks",
            "get_track_audio_features",
            "search_artists",
            "get_multiple_artists",
            "get_artist_tracks"
        ]

    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available tools.

        Returns:
            Dictionary mapping tool names to descriptions
        """
        descriptions = {}

        for tool_name in self.get_available_tools():
            tool = self.tools.get_tool(tool_name)
            if tool:
                descriptions[tool_name] = tool.description

        return descriptions