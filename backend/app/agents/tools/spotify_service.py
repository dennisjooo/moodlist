"""Spotify API service that coordinates all Spotify tools."""

import structlog
from typing import Dict, List, Optional, Any

from ..core.cache import cache_manager
from .agent_tools import AgentTools
from .spotify.user_data import GetUserTopTracksTool, GetUserTopArtistsTool
from .spotify.playlist_management import CreatePlaylistTool, AddTracksToPlaylistTool
from .spotify.user_profile import GetUserProfileTool
from .spotify.artist_search import SearchSpotifyArtistsTool, GetSeveralSpotifyArtistsTool, GetArtistTopTracksTool
from .spotify.track_search import SearchSpotifyTracksTool


logger = structlog.get_logger(__name__)


class SpotifyService:
    """Service for coordinating Spotify API operations."""

    def __init__(self):
        """Initialize the Spotify service."""
        self.tools = AgentTools()

        # Register all Spotify tools
        self._register_tools()

        logger.info("Initialized Spotify service with all tools")

    def _register_tools(self):
        """Register all Spotify tools."""
        tools_to_register = [
            GetUserTopTracksTool(),
            GetUserTopArtistsTool(),
            CreatePlaylistTool(),
            AddTracksToPlaylistTool(),
            GetUserProfileTool(),
            SearchSpotifyArtistsTool(),
            GetSeveralSpotifyArtistsTool(),
            GetArtistTopTracksTool(),
            SearchSpotifyTracksTool()
        ]

        for tool in tools_to_register:
            self.tools.register_tool(tool)

    async def get_user_top_tracks(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term",
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's top tracks with caching.

        Caches top tracks to avoid repeated API calls for identical requests.

        Args:
            access_token: Spotify access token
            limit: Number of tracks to return
            time_range: Time range for analysis
            user_id: Optional user ID for caching (recommended)

        Returns:
            List of user's top tracks
        """
        # Try to get from cache if user_id is provided
        if user_id:
            cached_tracks = await cache_manager.get_user_top_tracks(
                user_id=user_id,
                time_range=time_range,
                limit=limit
            )
            if cached_tracks is not None:
                logger.info(f"Cache hit for user {user_id} top tracks")
                return cached_tracks

        # Cache miss - fetch from API
        tool = self.tools.get_tool("get_user_top_tracks")
        if not tool:
            raise ValueError("User top tracks tool not available")

        result = await tool._run(
            access_token=access_token,
            limit=limit,
            time_range=time_range
        )

        if not result.success:
            logger.error(f"Failed to get user top tracks: {result.error}")
            return []

        tracks = result.data.get("tracks", [])

        # Cache the result if user_id is provided
        if user_id and tracks:
            await cache_manager.set_user_top_tracks(
                user_id=user_id,
                tracks=tracks,
                time_range=time_range,
                limit=limit
            )
            logger.info(f"Cached top tracks for user {user_id}")

        return tracks

    async def get_user_top_artists(
        self,
        access_token: str,
        limit: int = 20,
        time_range: str = "medium_term",
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's top artists with caching.

        Caches top artists to avoid repeated API calls for identical requests.

        Args:
            access_token: Spotify access token
            limit: Number of artists to return
            time_range: Time range for analysis
            user_id: Optional user ID for caching (recommended)

        Returns:
            List of user's top artists
        """
        # Try to get from cache if user_id is provided
        if user_id:
            cached_artists = await cache_manager.get_user_top_artists(
                user_id=user_id,
                time_range=time_range,
                limit=limit
            )
            if cached_artists is not None:
                logger.info(f"Cache hit for user {user_id} top artists")
                return cached_artists

        # Cache miss - fetch from API
        tool = self.tools.get_tool("get_user_top_artists")
        if not tool:
            raise ValueError("User top artists tool not available")

        result = await tool._run(
            access_token=access_token,
            limit=limit,
            time_range=time_range
        )

        if not result.success:
            logger.error(f"Failed to get user top artists: {result.error}")
            return []

        artists = result.data.get("artists", [])

        # Cache the result if user_id is provided
        if user_id and artists:
            await cache_manager.set_user_top_artists(
                user_id=user_id,
                artists=artists,
                time_range=time_range,
                limit=limit
            )
            logger.info(f"Cached top artists for user {user_id}")

        return artists

    async def get_user_profile(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user's Spotify profile.

        Args:
            access_token: Spotify access token

        Returns:
            User profile information or None if failed
        """
        tool = self.tools.get_tool("get_user_profile")
        if not tool:
            raise ValueError("User profile tool not available")

        result = await tool._run(access_token=access_token)

        if not result.success:
            logger.error(f"Failed to get user profile: {result.error}")
            return None

        return result.data

    async def create_playlist(
        self,
        access_token: str,
        name: str,
        description: str = "",
        public: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Create a new playlist.

        Args:
            access_token: Spotify access token
            name: Playlist name
            description: Playlist description
            public: Whether playlist is public

        Returns:
            Playlist information or None if failed
        """
        tool = self.tools.get_tool("create_playlist")
        if not tool:
            raise ValueError("Create playlist tool not available")

        result = await tool._run(
            access_token=access_token,
            name=name,
            description=description,
            public=public
        )

        if not result.success:
            logger.error(f"Failed to create playlist: {result.error}")
            return None

        return result.data

    async def add_tracks_to_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: List[str],
        position: Optional[int] = None
    ) -> bool:
        """Add tracks to a playlist.

        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            track_uris: List of track URIs to add
            position: Optional position for tracks

        Returns:
            Whether operation was successful
        """
        tool = self.tools.get_tool("add_tracks_to_playlist")
        if not tool:
            raise ValueError("Add tracks to playlist tool not available")

        result = await tool._run(
            access_token=access_token,
            playlist_id=playlist_id,
            track_uris=track_uris,
            position=position
        )

        if not result.success:
            logger.error(f"Failed to add tracks to playlist: {result.error}")
            return False

        return True

    async def search_spotify_artists(
        self,
        access_token: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for artists on Spotify.

        Args:
            access_token: Spotify access token
            query: Search query (artist name, genre, keywords)
            limit: Number of results to return

        Returns:
            List of artists matching the query
        """
        tool = self.tools.get_tool("search_spotify_artists")
        if not tool:
            raise ValueError("Search Spotify artists tool not available")

        result = await tool._run(
            access_token=access_token,
            query=query,
            limit=limit
        )

        if not result.success:
            logger.error(f"Failed to search Spotify artists: {result.error}")
            return []

        return result.data.get("artists", [])

    async def get_several_spotify_artists(
        self,
        access_token: str,
        artist_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get multiple artists from Spotify.

        Args:
            access_token: Spotify access token
            artist_ids: List of Spotify artist IDs (up to 50)

        Returns:
            List of artist data
        """
        tool = self.tools.get_tool("get_several_spotify_artists")
        if not tool:
            raise ValueError("Get several Spotify artists tool not available")

        result = await tool._run(
            access_token=access_token,
            artist_ids=artist_ids
        )

        if not result.success:
            logger.error(f"Failed to get several Spotify artists: {result.error}")
            return []

        return result.data.get("artists", [])

    async def get_artist_top_tracks(
        self,
        access_token: str,
        artist_id: str,
        market: str = "US"
    ) -> List[Dict[str, Any]]:
        """Get an artist's top tracks from Spotify.

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: ISO 3166-1 alpha-2 country code

        Returns:
            List of top tracks for the artist
        """
        tool = self.tools.get_tool("get_artist_top_tracks")
        if not tool:
            raise ValueError("Get artist top tracks tool not available")

        result = await tool._run(
            access_token=access_token,
            artist_id=artist_id,
            market=market
        )

        if not result.success:
            logger.error(f"Failed to get artist top tracks: {result.error}")
            return []

        return result.data.get("tracks", [])

    async def get_artist_hybrid_tracks(
        self,
        access_token: str,
        artist_id: str,
        market: str = "US",
        max_popularity: int = 80,
        min_popularity: int = 20,
        target_count: int = 10
    ) -> List[Dict[str, Any]]:
        """Get diverse tracks using hybrid strategy (top tracks + album deep cuts).

        This method provides better track diversity by combining:
        1. Filtered top tracks (avoiding mega-hits with popularity > max_popularity)
        2. Album tracks sampled from multiple albums

        Args:
            access_token: Spotify access token
            artist_id: Spotify artist ID
            market: ISO 3166-1 alpha-2 country code
            max_popularity: Maximum popularity threshold (default: 80, filters mega-hits)
            min_popularity: Minimum popularity threshold (default: 20, ensures quality)
            target_count: Target number of tracks to return (default: 10)

        Returns:
            List of diverse tracks from the artist
        """
        tool = self.tools.get_tool("get_artist_top_tracks")
        if not tool:
            raise ValueError("Get artist top tracks tool not available")

        try:
            tracks = await tool.get_hybrid_tracks(
                access_token=access_token,
                artist_id=artist_id,
                market=market,
                max_popularity=max_popularity,
                min_popularity=min_popularity,
                target_count=target_count
            )

            logger.info(
                f"Hybrid strategy returned {len(tracks)} tracks for artist {artist_id} "
                f"(popularity range: {min_popularity}-{max_popularity})"
            )
            return tracks

        except Exception as e:
            logger.error(f"Failed to get hybrid tracks for artist {artist_id}: {e}")
            # Fallback to regular top tracks if hybrid strategy fails
            logger.info("Falling back to regular top tracks")
            return await self.get_artist_top_tracks(
                access_token=access_token,
                artist_id=artist_id,
                market=market
            )

    async def search_spotify_tracks(
        self,
        access_token: str,
        query: str,
        limit: int = 20,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for tracks on Spotify.

        Args:
            access_token: Spotify access token
            query: Search query (track name, genre, keywords)
            limit: Number of results to return
            market: Optional ISO 3166-1 alpha-2 country code

        Returns:
            List of tracks matching the query
        """
        tool = self.tools.get_tool("search_spotify_tracks")
        if not tool:
            raise ValueError("Search Spotify tracks tool not available")

        result = await tool._run(
            access_token=access_token,
            query=query,
            limit=limit,
            market=market
        )

        if not result.success:
            logger.error(f"Failed to search Spotify tracks: {result.error}")
            return []

        return result.data.get("tracks", [])

    async def search_artists_by_genre(
        self,
        access_token: str,
        genre: str,
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """Search for artists in a specific genre.
        
        Args:
            access_token: Spotify access token
            genre: Genre to search for
            limit: Maximum number of artists to return
            
        Returns:
            List of artist dictionaries
        """
        try:
            search_query = f"genre:{genre}"
            
            # Use the existing search_spotify_artists method which handles the API call
            artists = await self.search_spotify_artists(
                access_token=access_token,
                query=search_query,
                limit=min(limit, 50)  # Spotify API max is 50
            )
            
            logger.info(f"Found {len(artists)} artists for genre: {genre}")
            return artists
            
        except Exception as e:
            logger.error(f"Failed to search artists by genre '{genre}': {e}")
            return []

    async def search_tracks_for_artists(
        self,
        access_token: str,
        query: str,
        limit: int = 20,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for tracks and extract unique artists from results.

        Args:
            access_token: Spotify access token
            query: Search query (genre, keywords, etc.)
            limit: Number of track results to fetch
            market: Optional ISO 3166-1 alpha-2 country code

        Returns:
            List of unique artists extracted from track results
        """
        # Search for tracks
        tracks = await self.search_spotify_tracks(
            access_token=access_token,
            query=query,
            limit=limit,
            market=market
        )

        if not tracks:
            logger.warning(f"No tracks found for query '{query}'")
            return []

        # Extract unique artists from tracks
        artists = []
        seen_ids = set()

        for track in tracks:
            for artist in track.get("artists", []):
                artist_id = artist.get("id")
                if artist_id and artist_id not in seen_ids:
                    seen_ids.add(artist_id)
                    # Create artist info structure matching SearchSpotifyArtistsTool output
                    artists.append({
                        "id": artist_id,
                        "name": artist.get("name"),
                        "spotify_uri": artist.get("uri"),
                        "genres": [],  # Track search doesn't return genres, would need separate call
                        "popularity": None,  # Not available in track artist data
                        "followers": None,  # Not available in track artist data
                        "images": []  # Not available in track artist data
                    })

        logger.info(f"Extracted {len(artists)} unique artists from {len(tracks)} tracks for query '{query}'")
        return artists

    async def upload_playlist_cover_image(
        self,
        access_token: str,
        playlist_id: str,
        image_base64: str
    ) -> bool:
        """Upload a custom cover image to a Spotify playlist.

        Args:
            access_token: Spotify access token
            playlist_id: Spotify playlist ID
            image_base64: Base64-encoded JPEG image data

        Returns:
            Whether the upload was successful
        """
        import aiohttp
        
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "image/jpeg"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, data=image_base64) as response:
                    if response.status == 202:
                        logger.info(f"Successfully uploaded cover image to playlist {playlist_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to upload cover image: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error uploading playlist cover image: {str(e)}", exc_info=True)
            return False

    def get_available_tools(self) -> List[str]:
        """Get list of available Spotify tools.

        Returns:
            List of tool names
        """
        return [
            "get_user_top_tracks",
            "get_user_top_artists",
            "get_user_profile",
            "create_playlist",
            "add_tracks_to_playlist",
            "search_spotify_artists",
            "get_several_spotify_artists",
            "get_artist_top_tracks",
            "search_spotify_tracks"
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
