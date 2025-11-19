"""Artist processing utilities for anchor track selection."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional

from ...utils.config import config
from .track_processor import TrackProcessor

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
        self.track_processor = TrackProcessor(reccobeat_service)

    async def get_artist_based_candidates(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_analysis: Optional[Dict[str, Any]] = None,
        user_mentioned_artists: Optional[List[str]] = None,
        skip_audio_features: bool = False,
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

        # Extract temporal context for filtering
        temporal_context = (
            mood_analysis.get("temporal_context") if mood_analysis else None
        )

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
            artist_infos,
            mentioned_artists,
            target_features,
            access_token,
            temporal_context,
            skip_audio_features=skip_audio_features,
        )

        return candidates

    def _categorize_and_prioritize_artists(
        self,
        artist_recommendations: List[str],
        mood_prompt: str,
        user_mentioned_artists: Optional[List[str]],
    ) -> tuple[List[str], List[str]]:
        """Categorize artists into mentioned vs others and create prioritized list.

        Args:
            artist_recommendations: All recommended artist names
            mood_prompt: User's mood prompt (unused, kept for compatibility)
            user_mentioned_artists: Artists from intent analysis

        Returns:
            Tuple of (mentioned_artists, artists_to_process)
        """
        user_mentioned_set = {
            artist.lower() if artist else ""
            for artist in (user_mentioned_artists or [])
        }

        mentioned_artists = []
        other_artists = []

        for artist in artist_recommendations:
            if not artist:
                continue

            # CRITICAL FIX: Only check user_mentioned_set from IntentAnalyzer
            # DO NOT check if artist name appears in prompt text - that's too broad
            # and incorrectly marks artists like "The Notorious B.I.G." as user-mentioned
            # when they're just in mood recommendations or user's listening history
            is_user_mentioned = artist.lower() in user_mentioned_set

            if is_user_mentioned:
                mentioned_artists.append(artist)
                logger.info(
                    f"✓ Detected user-mentioned artist for anchor search: {artist}"
                )
            else:
                other_artists.append(artist)
        # PERFORMANCE: Process ALL user-mentioned artists first (no limit), then other artists
        max_artists = config.artist_anchor_processing_limit
        artists_to_process = (
            mentioned_artists
            + other_artists[: max(0, max_artists - len(mentioned_artists))]
        )

        logger.info(
            f"Processing {len(artists_to_process)} artists for anchors (limit: {max_artists}): "
            f"{len(mentioned_artists)} user-mentioned + {len(artists_to_process) - len(mentioned_artists)} others"
        )

        return mentioned_artists, artists_to_process

    async def _search_artists(
        self,
        artists_to_process: List[str],
        mentioned_artists: List[str],
        access_token: str,
    ) -> List[Dict[str, Any]]:
        """Search for artists on Spotify in parallel and return validated artist info.

        Performs parallel artist searches to reduce latency.

        Args:
            artists_to_process: List of artist names to search
            mentioned_artists: List of user-mentioned artist names
            access_token: Spotify access token

        Returns:
            List of dicts with 'info', 'name', and 'is_mentioned' keys
        """

        async def search_single_artist(artist_name: str) -> Optional[Dict[str, Any]]:
            """Search for a single artist and return info if found."""
            try:
                logger.info(f"Searching for artist: {artist_name}")

                artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=artist_name,
                    limit=config.artist_search_limit,
                )

                if not artists:
                    return None

                # Find the artist with exact name match (case-insensitive)
                artist_info = None
                for artist_result in artists:
                    if artist_result.get("name", "").lower() == artist_name.lower():
                        artist_info = artist_result
                        break

                # If no exact match, fall back to first result
                if not artist_info:
                    logger.warning(
                        f"No exact match for '{artist_name}', using closest match: {artists[0].get('name')}"
                    )
                    artist_info = artists[0]

                artist_id = artist_info.get("id")
                if artist_id:
                    is_mentioned_check = artist_name in mentioned_artists
                    return {
                        "info": artist_info,
                        "name": artist_name,
                        "is_mentioned": is_mentioned_check,
                    }

                return None

            except Exception as e:
                logger.warning(f"Failed to search for artist '{artist_name}': {e}")
                return None

        # Search all artists concurrently (performance: limit to processed subset)
        artists_to_search = artists_to_process
        logger.info(f"Searching for {len(artists_to_search)} artists in parallel")

        search_results = await asyncio.gather(
            *[search_single_artist(artist_name) for artist_name in artists_to_search],
            return_exceptions=True,
        )

        # Filter out None results and exceptions
        artist_infos = []
        for result in search_results:
            if result and not isinstance(result, Exception):
                artist_infos.append(result)

        logger.info(
            f"Found {len(artist_infos)} artists out of {len(artists_to_search)} searches"
        )
        return artist_infos

    async def _fetch_artist_tracks(
        self,
        artist_infos: List[Dict[str, Any]],
        mentioned_artists: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        temporal_context: Optional[Dict[str, Any]] = None,
        skip_audio_features: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch top tracks for each artist using batch method and create anchor candidates.

        Uses batch fetching to respect rate limits while maintaining performance.

        Args:
            artist_infos: List of validated artist info dicts
            mentioned_artists: List of user-mentioned artist names
            target_features: Target audio features
            access_token: Spotify access token
            temporal_context: Temporal context for filtering tracks

        Returns:
            List of anchor candidate dictionaries
        """
        if not artist_infos:
            return []

        # Extract artist IDs and create mapping
        artist_id_to_data = {}
        artist_ids = []
        for artist_data in artist_infos:
            artist_info = artist_data["info"]
            artist_id = artist_info.get("id")
            if artist_id:
                artist_id_to_data[artist_id] = artist_data
                artist_ids.append(artist_id)

        if not artist_ids:
            return []

        # Batch fetch all artist top tracks at once (respects rate limits)
        logger.info(f"Batch fetching top tracks for {len(artist_ids)} artists")
        prefetched_tracks = await self.spotify_service.get_artist_top_tracks_batch(
            access_token=access_token,
            artist_ids=artist_ids,
            max_concurrency=config.artist_top_tracks_max_concurrency,
        )

        # Process tracks for each artist
        candidates = []
        for artist_id, tracks in prefetched_tracks.items():
            artist_data = artist_id_to_data.get(artist_id)
            if not artist_data or not tracks:
                continue

            artist_name = artist_data["name"]
            # Take configurable number of tracks based on whether artist was user mentioned
            limit_per_artist = (
                config.mentioned_artist_track_limit
                if artist_name in mentioned_artists
                else config.default_artist_track_limit
            )
            selected_tracks = tracks[:limit_per_artist]

            # Create candidates for each track
            for track in selected_tracks:
                candidate = await self._create_artist_candidate(
                    track,
                    artist_name,
                    artist_data["is_mentioned"],
                    target_features,
                    temporal_context,
                )
                if candidate:
                    candidates.append(candidate)

        # Batch fetch all audio features at once (unless skipped for coordinated batching)
        if not skip_audio_features and candidates and self.reccobeat_service:
            track_ids = [
                c["track"]["id"] for c in candidates if c.get("track", {}).get("id")
            ]
            if track_ids:
                try:
                    logger.info(
                        f"Batch fetching audio features for {len(track_ids)} tracks"
                    )
                    features_map = (
                        await self.reccobeat_service.get_tracks_audio_features(
                            track_ids
                        )
                    )

                    # Update candidates with batched features
                    for candidate in candidates:
                        track_id = candidate.get("track", {}).get("id")
                        if track_id and track_id in features_map:
                            candidate["track"]["audio_features"] = features_map[
                                track_id
                            ]
                            candidate["features"] = features_map[track_id]

                    logger.info(
                        f"Successfully enriched {len([c for c in candidates if c.get('features')])} candidates with audio features"
                    )
                except Exception as e:
                    logger.warning(f"Failed to batch fetch audio features: {e}")

        logger.info(
            f"Created {len(candidates)} anchor candidates from {len(artist_infos)} artists"
        )
        return candidates

    async def _create_artist_candidate(
        self,
        track: Dict[str, Any],
        artist_name: str,
        is_mentioned: bool,
        target_features: Dict[str, Any],
        temporal_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an anchor candidate from an artist track.

        Audio features are batch fetched after candidates are collected, so this
        method no longer fetches them individually.

        Args:
            track: Track dictionary from Spotify
            artist_name: Name of the artist
            is_mentioned: Whether the artist was mentioned in the prompt
            target_features: Target audio features
            temporal_context: Temporal context for filtering

        Returns:
            Anchor candidate dictionary or None if invalid
        """
        if not track.get("id"):
            return None

        # CRITICAL: Apply temporal filtering BEFORE marking as protected
        # This prevents temporally mismatched tracks from becoming protected anchors
        is_temporal_match, temporal_reason = self.track_processor.check_temporal_match(
            track, temporal_context
        )
        if not is_temporal_match:
            artist_mention_status = "user-mentioned" if is_mentioned else "recommended"
            logger.info(
                f"✗ Filtered {artist_mention_status} artist track '{track.get('name')}' "
                f"by {artist_name}: {temporal_reason}"
            )
            return None

        # Audio features will be batch fetched after all candidates are collected
        # Initialize with empty features dict
        features = {}

        # Mark as artist-based anchor
        track["user_mentioned"] = is_mentioned  # Mentioned artists get high priority
        track["anchor_type"] = (
            "artist_mentioned" if is_mentioned else "artist_recommended"
        )
        track["protected"] = is_mentioned  # Protect mentioned artist tracks

        return {
            "track": track,
            "score": 0.9 if is_mentioned else 0.8,  # High base score for artist tracks
            "confidence": 0.95 if is_mentioned else 0.9,
            "features": features,
            "artist": artist_name,
            "source": "artist_top_tracks",
            "anchor_type": track["anchor_type"],
            "user_mentioned": is_mentioned,
            "protected": is_mentioned,
        }
