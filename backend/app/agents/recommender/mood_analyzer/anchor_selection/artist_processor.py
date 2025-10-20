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
        mood_analysis: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from top recommended artists, prioritizing those mentioned in prompt.

        Args:
            mood_prompt: User's mood prompt
            artist_recommendations: List of artist names from mood analysis
            target_features: Target audio features
            access_token: Spotify access token
            mood_analysis: Mood analysis context

        Returns:
            List of artist-based track candidate dictionaries
        """
        if not self.spotify_service or not artist_recommendations:
            return []

        candidates = []
        prompt_lower = mood_prompt.lower()

        # Prioritize artists mentioned in the prompt
        mentioned_artists = []
        other_artists = []

        for artist in artist_recommendations:
            if artist.lower() in prompt_lower:
                mentioned_artists.append(artist)
            else:
                other_artists.append(artist)

        # Process mentioned artists first (up to 3), then other top artists (up to 5 total)
        artists_to_process = mentioned_artists[:3] + other_artists[:5]

        # First, fetch all artist info
        artist_infos = []
        for artist_name in artists_to_process[:8]:  # Limit to 8 artists total
            try:
                logger.info(f"Searching for artist: {artist_name}")

                # Search for artist first to get the Spotify artist ID
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

        # Now fetch tracks for validated artists
        for artist_data in artist_infos:
            artist_info = artist_data['info']
            artist_name = artist_data['name']
            artist_id = artist_info.get('id')

            try:
                # Get top tracks for this artist
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