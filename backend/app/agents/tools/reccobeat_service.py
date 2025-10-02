"""RecoBeat API service that coordinates all RecoBeat tools."""

import logging
from typing import Dict, List, Optional, Any

from .agent_tools import AgentTools
from .reccobeat.track_recommendations import TrackRecommendationsTool
from .reccobeat.track_info import GetMultipleTracksTool, GetTrackAudioFeaturesTool
from .reccobeat.artist_info import SearchArtistTool, GetMultipleArtistsTool, GetArtistTracksTool


logger = logging.getLogger(__name__)


class RecoBeatService:
    """Service for coordinating RecoBeat API operations."""

    def __init__(self):
        """Initialize the RecoBeat service."""
        self.tools = AgentTools()

        # Register all RecoBeat tools
        self._register_tools()

        logger.info("Initialized RecoBeat service with all tools")

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

        return result.data.get("recommendations", [])

    async def convert_spotify_tracks_to_reccobeat(
        self,
        spotify_track_ids: List[str]
    ) -> Dict[str, str]:
        """Convert Spotify track IDs to RecoBeat IDs using batch lookup.

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
        
        # Process in chunks of 40 (API limit)
        for i in range(0, len(spotify_track_ids), 40):
            chunk = spotify_track_ids[i:i + 40]
            
            try:
                result = await tracks_tool._run(ids=chunk)
                
                if result.success:
                    tracks = result.data.get("tracks", [])
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
                                if orig_id not in id_mapping:
                                    spotify_id = orig_id
                                    break
                        
                        if reccobeat_id:
                            id_mapping[spotify_id] = reccobeat_id
                            
            except Exception as e:
                logger.debug(f"Error converting track IDs chunk: {e}")
                continue
        
        logger.info(f"Converted {len(id_mapping)}/{len(spotify_track_ids)} Spotify track IDs to RecoBeat IDs")
        return id_mapping

    async def get_tracks_audio_features(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get audio features for multiple tracks.

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

        # Try to convert Spotify IDs to RecoBeat IDs first
        id_mapping = await self.convert_spotify_tracks_to_reccobeat(track_ids)
        logger.info(f"Successfully converted {len(id_mapping)}/{len(track_ids)} Spotify tracks to RecoBeat IDs")
        
        # Get features for each track (only if we have a valid RecoBeat ID)
        for track_id in track_ids:
            # Skip if we couldn't convert the Spotify ID to RecoBeat ID
            if track_id not in id_mapping:
                logger.debug(f"Skipping track {track_id} - not found in RecoBeat database")
                continue
            
            reccobeat_id = id_mapping[track_id]
            
            try:
                result = await features_tool._run(track_id=reccobeat_id)
                if result.success:
                    # Map back to original Spotify ID
                    features_map[track_id] = result.data
                else:
                    # 404 errors are common - track might not exist in RecoBeat
                    if "404" in str(result.error):
                        logger.debug(f"Track {reccobeat_id} not found in RecoBeat (404)")
                    else:
                        logger.warning(f"Failed to get features for track {reccobeat_id}: {result.error}")
            except Exception as e:
                # 404 errors are expected for many Spotify tracks
                if "404" in str(e):
                    logger.debug(f"Track {reccobeat_id} not found in RecoBeat: {e}")
                else:
                    logger.error(f"Error getting features for track {reccobeat_id}: {e}")

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
        """Get track information for multiple track IDs.

        Args:
            track_ids: List of track IDs

        Returns:
            List of track information
        """
        # Split into chunks to respect API limits (40 per request)
        chunk_size = 40
        all_tracks = []

        for i in range(0, len(track_ids), chunk_size):
            chunk = track_ids[i:i + chunk_size]

            tracks_tool = self.tools.get_tool("get_multiple_tracks")
            if not tracks_tool:
                logger.warning("Multiple tracks tool not available")
                continue

            try:
                result = await tracks_tool._run(ids=chunk)
                if result.success:
                    tracks = result.data.get("tracks", [])
                    all_tracks.extend(tracks)
                else:
                    logger.warning(f"Failed to get tracks for chunk {i//chunk_size}: {result.error}")

            except Exception as e:
                logger.error(f"Error getting tracks for chunk {i//chunk_size}: {e}")

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