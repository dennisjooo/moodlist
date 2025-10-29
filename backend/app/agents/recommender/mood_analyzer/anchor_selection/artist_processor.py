"""Artist processing utilities for anchor track selection."""

import structlog
from typing import Any, Dict, List, Optional

from .types import AnchorCandidate

logger = structlog.get_logger(__name__)


class ArtistProcessor:
    """Handles artist-based track discovery and processing."""

    def __init__(self, spotify_service=None, reccobeat_service=None):
        """Initialize the artist processor.

        Args:
            spotify_service: SpotifyService for artist search
            reccobeat_service: RecoBeatService for audio features
        """
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

    async def get_artist_based_candidates(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_analysis: Optional[Dict[str, Any]] = None,
        user_mentioned_artists: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from top recommended artists, prioritizing those mentioned in prompt.

        Args:
            mood_prompt: User's mood prompt
            artist_recommendations: List of artist names from mood analysis (already prioritized if user mentions exist)
            target_features: Target audio features
            access_token: Spotify access token
            mood_analysis: Mood analysis context
            user_mentioned_artists: Artists explicitly mentioned by user from intent analysis

        Returns:
            List of artist-based track candidate dictionaries
        """
        if not self.spotify_service or not artist_recommendations:
            return []

        # Step 1: Categorize artists (mentioned vs others)
        mentioned_artists, artists_to_process = self._categorize_and_prioritize_artists(
            artist_recommendations, mood_prompt, user_mentioned_artists
        )

        # Step 2: Search for artist IDs on Spotify
        artist_infos = await self._search_artists(
            artists_to_process, mentioned_artists, access_token
        )

        # Step 3: Fetch tracks for each validated artist
        candidates = await self._fetch_artist_tracks(
            artist_infos, mentioned_artists, target_features, access_token
        )

        return candidates

    def _categorize_and_prioritize_artists(
        self,
        artist_recommendations: List[str],
        mood_prompt: str,
        user_mentioned_artists: Optional[List[str]]
    ) -> tuple[List[str], List[str]]:
        """Categorize artists into mentioned vs others and create prioritized list.

        Args:
            artist_recommendations: All recommended artist names
            mood_prompt: User's mood prompt
            user_mentioned_artists: Artists from intent analysis

        Returns:
            Tuple of (mentioned_artists, artists_to_process)
        """
        prompt_lower = mood_prompt.lower()
        user_mentioned_set = {artist.lower() if artist else '' for artist in (user_mentioned_artists or [])}

        mentioned_artists = []
        other_artists = []

        for artist in artist_recommendations:
            if not artist:
                continue
                
            # Check if artist is in user-mentioned set OR in the prompt text (case-insensitive)
            is_user_mentioned = (
                artist.lower() in user_mentioned_set or
                artist.lower() in prompt_lower
            )
            
            if is_user_mentioned:
                mentioned_artists.append(artist)
                logger.info(f"✓ Detected user-mentioned artist for anchor search: {artist}")
            else:
                other_artists.append(artist)

        # CRITICAL: Process ALL user-mentioned artists first (no limit), then other artists
        artists_to_process = mentioned_artists + other_artists[:max(0, 8 - len(mentioned_artists))]
        
        logger.info(
            f"Processing {len(artists_to_process)} artists for anchors: "
            f"{len(mentioned_artists)} user-mentioned + {len(artists_to_process) - len(mentioned_artists)} others"
        )

        return mentioned_artists, artists_to_process

    async def _search_artists(
        self,
        artists_to_process: List[str],
        mentioned_artists: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Search for artists on Spotify and return validated artist info.

        Args:
            artists_to_process: List of artist names to search
            mentioned_artists: List of user-mentioned artist names
            access_token: Spotify access token

        Returns:
            List of dicts with 'info', 'name', and 'is_mentioned' keys
        """
        artist_infos = []
        
        for artist_name in artists_to_process[:8]:  # Limit to 8 artists total
            try:
                logger.info(f"Searching for artist: {artist_name}")

                artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=artist_name,
                    limit=1
                )

                if not artists:
                    continue

                artist_info = artists[0]
                artist_id = artist_info.get('id')
                if artist_id:
                    artist_infos.append({
                        'info': artist_info,
                        'name': artist_name,
                        'is_mentioned': artist_name in mentioned_artists
                    })

            except Exception as e:
                logger.warning(f"Failed to search for artist '{artist_name}': {e}")
                continue

        return artist_infos

    async def _fetch_artist_tracks(
        self,
        artist_infos: List[Dict[str, Any]],
        mentioned_artists: List[str],
        target_features: Dict[str, Any],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Fetch top tracks for each artist and create anchor candidates.

        Args:
            artist_infos: List of validated artist info dicts
            mentioned_artists: List of user-mentioned artist names
            target_features: Target audio features
            access_token: Spotify access token

        Returns:
            List of anchor candidate dictionaries
        """
        candidates = []

        for artist_data in artist_infos:
            artist_info = artist_data['info']
            artist_name = artist_data['name']
            artist_id = artist_info.get('id')

            try:
                tracks = await self.spotify_service.get_artist_top_tracks(
                    access_token=access_token,
                    artist_id=artist_id,
                    market='US'  # Could be made configurable
                )

                if not tracks:
                    continue

                # Take top 2 tracks per artist for mentioned artists, 1 for others
                limit_per_artist = 2 if artist_name in mentioned_artists else 1
                selected_tracks = tracks[:limit_per_artist]

                # Create candidates for each track
                for track in selected_tracks:
                    candidate = await self._create_artist_candidate(
                        track, artist_name, artist_data['is_mentioned'], target_features
                    )
                    if candidate:
                        candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Failed to get tracks for artist '{artist_name}': {e}")
                continue

        return candidates

    async def _create_artist_candidate(
        self,
        track: Dict[str, Any],
        artist_name: str,
        is_mentioned: bool,
        target_features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create an anchor candidate from an artist track.

        Args:
            track: Track dictionary from Spotify
            artist_name: Name of the artist
            is_mentioned: Whether the artist was mentioned in the prompt
            target_features: Target audio features

        Returns:
            Anchor candidate dictionary or None if invalid
        """
        if not track.get('id'):
            return None

        # Get audio features if available
        features = {}
        if self.reccobeat_service:
            try:
                features_map = await self.reccobeat_service.get_tracks_audio_features([track['id']])
                features = features_map.get(track['id'], {})
                track['audio_features'] = features
            except Exception as e:
                logger.warning(f"Failed to get features for artist track: {e}")

        # Mark as artist-based anchor
        track['user_mentioned'] = is_mentioned  # Mentioned artists get high priority
        track['anchor_type'] = 'artist_mentioned' if is_mentioned else 'artist_recommended'
        track['protected'] = is_mentioned  # Protect mentioned artist tracks

        return {
            'track': track,
            'score': 0.9 if is_mentioned else 0.8,  # High base score for artist tracks
            'confidence': 0.95 if is_mentioned else 0.9,
            'features': features,
            'artist': artist_name,
            'source': 'artist_top_tracks',
            'anchor_type': track['anchor_type'],
            'user_mentioned': is_mentioned,
            'protected': is_mentioned
        }