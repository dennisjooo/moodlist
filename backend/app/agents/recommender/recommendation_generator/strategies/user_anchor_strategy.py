"""User anchor strategy for recommendations based on user-mentioned tracks."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional, Tuple

from ....states.agent_state import AgentState
from .base_strategy import RecommendationStrategy
from ...utils.temporal_filter import check_temporal_match

logger = structlog.get_logger(__name__)


class UserAnchorStrategy(RecommendationStrategy):
    """Strategy that generates recommendations based on user-mentioned tracks and artists.
    
    This strategy:
    1. Gets user-mentioned tracks from SeedGathererAgent
    2. Uses Spotify's "Get Recommendations" API with ONLY those tracks as seeds
    3. Fetches artist's top tracks for mentioned artists
    4. Marks all results as high confidence
    """

    def __init__(self, spotify_service, reccobeat_service=None):
        """Initialize the user anchor strategy.

        Args:
            spotify_service: SpotifyService for API calls
            reccobeat_service: RecoBeatService (optional, for feature enrichment)
        """
        super().__init__(name="user_anchor")
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

    def _check_temporal_match(
        self,
        track: Dict[str, Any],
        temporal_context: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Check if a track matches the temporal context requirements.

        Args:
            track: Track dictionary from Spotify (should have album.release_date)
            temporal_context: Temporal context from mood analysis

        Returns:
            Tuple of (is_match, reason) - (True, None) if matches or no constraint,
            (False, reason) if violates temporal requirement
        """
        return check_temporal_match(track, temporal_context)

    async def generate_recommendations(
        self,
        state: AgentState,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on user-mentioned tracks/artists.

        Args:
            state: Current agent state with user mentions
            target_count: Target number of recommendations

        Returns:
            List of recommendation dictionaries with high confidence scores
        """
        recommendations = []

        # Get user-mentioned tracks from metadata (set by SeedGathererAgent)
        user_mentioned_track_ids = state.metadata.get("user_mentioned_track_ids", [])
        user_mentioned_tracks_full = state.metadata.get("user_mentioned_tracks_full", [])
        intent_analysis = state.metadata.get("intent_analysis", {})
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])

        # CRITICAL: Get temporal context for filtering
        temporal_context = state.mood_analysis.get('temporal_context') if state.mood_analysis else None

        if not user_mentioned_track_ids and not user_mentioned_artists:
            logger.info("No user-mentioned tracks or artists, user anchor strategy skipped")
            return []

        logger.info(
            f"User anchor strategy: {len(user_mentioned_track_ids)} tracks, "
            f"{len(user_mentioned_artists)} artists"
        )

        # Get access token
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.warning("No access token for user anchor strategy")
            return []

        # Track which track IDs we've already added to prevent duplicates
        added_track_ids = set()

        # PART 0: ALWAYS include the actual user-mentioned tracks themselves!
        if user_mentioned_tracks_full:
            user_track_recs = self._add_user_mentioned_tracks(user_mentioned_tracks_full, temporal_context)
            recommendations.extend(user_track_recs)
            # Track the IDs we just added
            for rec in user_track_recs:
                if rec.get("track_id"):
                    added_track_ids.add(rec["track_id"])

        # PART 1: Get artists from user-mentioned tracks and fetch their top tracks
        if user_mentioned_track_ids:
            track_based_recs = await self._get_tracks_from_same_artists(
                user_mentioned_tracks_full,
                access_token,
                target_count // 2 if user_mentioned_artists else target_count,
                temporal_context,
                exclude_track_ids=added_track_ids  # Pass exclusion set
            )
            recommendations.extend(track_based_recs)
            # Track newly added IDs
            for rec in track_based_recs:
                if rec.get("track_id"):
                    added_track_ids.add(rec["track_id"])
            logger.info(f"Got {len(track_based_recs)} tracks from user-mentioned track artists")

        # PART 2: Get top tracks from user-mentioned artists
        if user_mentioned_artists:
            artist_based_recs = await self._get_top_tracks_from_artists(
                user_mentioned_artists,
                access_token,
                target_count // 2 if user_mentioned_track_ids else target_count,
                temporal_context,
                exclude_track_ids=added_track_ids  # Pass exclusion set
            )
            recommendations.extend(artist_based_recs)
            
            # CRITICAL: Log prominently if we failed to get tracks for user-mentioned artists
            if len(artist_based_recs) == 0:
                logger.error(
                    f"FAILED to get any tracks from user-mentioned artists: {user_mentioned_artists}. "
                    f"This is a critical failure - user explicitly requested these artists!"
                )
            else:
                logger.info(
                    f"✓ Got {len(artist_based_recs)} top tracks from {len(user_mentioned_artists)} "
                    f"user-mentioned artist(s): {', '.join(user_mentioned_artists)}"
                )

        # Mark all recommendations with high confidence
        self._mark_recommendations_with_confidence(recommendations)

        logger.info(f"User anchor strategy generated {len(recommendations)} recommendations")

        return recommendations[:target_count]

    def _add_user_mentioned_tracks(
        self,
        user_mentioned_tracks_full: List[Dict[str, Any]],
        temporal_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Add the actual user-mentioned tracks to recommendations.

        IMPORTANT: These are EXPLICIT user track mentions - we do NOT filter them by temporal context.
        If the user explicitly asks for a track, they get it regardless of era/decade constraints.

        Args:
            user_mentioned_tracks_full: List of full track dictionaries
            temporal_context: Temporal context (unused for explicit mentions)

        Returns:
            List of recommendation dictionaries for user-mentioned tracks
        """
        recommendations = []

        for track in user_mentioned_tracks_full:
            track_id = track.get("id")
            track_name = track.get("name", "Unknown")
            artist_name = track.get("artist", "Unknown Artist")

            # Build Spotify URI if missing
            spotify_uri = track.get("uri")
            if not spotify_uri and track_id:
                spotify_uri = f"spotify:track:{track_id}"

            # Try to get audio features if available
            audio_features = track.get("audio_features", {})

            # Build the recommendation with all required fields
            user_track_rec = {
                "track_id": track_id,
                "track_name": track_name,
                "artists": [artist_name],
                "spotify_uri": spotify_uri,
                "confidence": 1.0,  # Maximum confidence - user explicitly requested this
                "confidence_score": 1.0,  # Also set confidence_score for compatibility
                "audio_features": audio_features,
                "source": "anchor_track",  # CRITICAL: Must be anchor_track so it's recognized by the processor
                "reasoning": f"User explicitly mentioned this track: '{track_name}' by {artist_name}",
                "user_mentioned": True,
                "protected": True,
                "anchor_type": "user"
            }

            recommendations.append(user_track_rec)
            logger.info(
                f"✓ Added user-mentioned track: '{track_name}' by {artist_name} "
                f"(ID: {track_id}, URI: {spotify_uri}, source: anchor_track, PROTECTED from temporal filtering)"
            )

        logger.info(f"✓ Total {len(recommendations)} user-mentioned tracks added (no temporal filtering for explicit mentions)")
        return recommendations

    def _mark_recommendations_with_confidence(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Mark all recommendations with high confidence and protection flags.

        Args:
            recommendations: List of recommendation dictionaries to modify in-place
        """
        # CRITICAL: Use "anchor_track" as source for user-mentioned artist tracks so they're protected
        for rec in recommendations:
            # If this is the actual user-mentioned track, it already has source="anchor_track"
            # For tracks from user-mentioned artists, also mark as anchor_track but with user_mentioned_artist flag
            if not rec.get("user_mentioned"):
                rec["source"] = "anchor_track"  # CHANGED: Use anchor_track for protection
                rec["user_mentioned_artist"] = True  # Flag that this is from a user-mentioned artist
                rec["protected"] = True  # Protect from filtering
                rec["confidence_boost"] = 0.3  # Boost confidence for user mentions
                rec["user_mentioned_related"] = True
                # Set base confidence high since these are directly related to user intent
                if "confidence" not in rec:
                    rec["confidence"] = 0.95  # Higher confidence than generic artist discovery
                if "confidence_score" not in rec:
                    rec["confidence_score"] = 0.95  # FIXED: Also set confidence_score for proper sorting

    async def _get_tracks_from_same_artists(
        self,
        user_mentioned_tracks: List[Dict[str, Any]],
        access_token: str,
        limit: int,
        temporal_context: Optional[Dict[str, Any]] = None,
        exclude_track_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Get top tracks from artists of user-mentioned tracks.

        Args:
            user_mentioned_tracks: List of user-mentioned track dictionaries with artist info
            access_token: Spotify access token
            limit: Maximum number of tracks
            temporal_context: Temporal context for filtering
            exclude_track_ids: Set of track IDs to exclude (to prevent duplicates)

        Returns:
            List of recommendation dictionaries
        """
        try:
            # Extract unique artist IDs
            artist_ids_seen = self._extract_unique_artist_ids(user_mentioned_tracks)

            if not artist_ids_seen:
                return []

            # Get MORE tracks from user-mentioned artists (5-7 per artist instead of 2-3)
            tracks_per_artist = max(5, min(7, limit // len(artist_ids_seen)))

            logger.info(
                f"Getting {tracks_per_artist} tracks from each of {len(artist_ids_seen)} "
                f"user-mentioned track artists (limit: {limit})"
            )

            # Get top tracks for each artist
            recommendations = await self._fetch_tracks_for_artists(
                artist_ids_seen,
                access_token,
                tracks_per_artist,
                temporal_context,
                exclude_track_ids=exclude_track_ids
            )

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error getting tracks from same artists: {e}", exc_info=True)
            return []

    def _extract_unique_artist_ids(
        self,
        user_mentioned_tracks: List[Dict[str, Any]]
    ) -> set:
        """Extract unique artist IDs from user-mentioned tracks.

        Args:
            user_mentioned_tracks: List of track dictionaries

        Returns:
            Set of unique artist IDs
        """
        artist_ids_seen = set()
        
        for track in user_mentioned_tracks:
            artist_id = track.get("artist_id")
            if artist_id and artist_id not in artist_ids_seen:
                artist_ids_seen.add(artist_id)
        
        return artist_ids_seen

    async def _fetch_tracks_for_artists(
        self,
        artist_ids: set,
        access_token: str,
        tracks_per_artist: int,
        temporal_context: Optional[Dict[str, Any]] = None,
        exclude_track_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Fetch top tracks for a set of artist IDs.

        Args:
            artist_ids: Set of artist IDs
            access_token: Spotify access token
            tracks_per_artist: Number of tracks to fetch per artist
            temporal_context: Temporal context for filtering
            exclude_track_ids: Set of track IDs to exclude (to prevent duplicates)

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        exclude_track_ids = exclude_track_ids or set()
        skipped_duplicates = 0

        for artist_id in artist_ids:
            try:
                # Use hybrid strategy favoring top tracks for user-mentioned artists
                # Users explicitly requested these artists, so favor their popular/recognizable tracks
                top_tracks = await self.spotify_service.get_artist_hybrid_tracks(
                    artist_id=artist_id,
                    access_token=access_token,
                    max_popularity=95,  # Allow popular tracks (users want hits from mentioned artists)
                    min_popularity=30,  # Ensure decent quality
                    target_count=tracks_per_artist,
                    top_tracks_ratio=0.9  # Popular-focused: 90% top tracks, 10% album tracks
                )

                for track in top_tracks:
                    if not track.get("id"):
                        continue

                    # Skip if this track was already added
                    if track["id"] in exclude_track_ids:
                        skipped_duplicates += 1
                        logger.debug(
                            f"Skipping duplicate track: '{track.get('name')}' (already added as user-mentioned track)"
                        )
                        continue

                    # CRITICAL: Apply temporal filtering BEFORE marking as protected
                    is_temporal_match, temporal_reason = self._check_temporal_match(track, temporal_context)
                    if not is_temporal_match:
                        artists = [a.get("name", "") for a in track.get("artists", [])]
                        logger.info(
                            f"✗ Filtered user-mentioned artist track '{track.get('name')}' "
                            f"by {', '.join(artists)}: {temporal_reason}"
                        )
                        continue

                    # Build proper artist list
                    artists = [a.get("name", "") for a in track.get("artists", [])]

                    recommendations.append({
                        "track_id": track["id"],
                        "track_name": track.get("name", ""),
                        "artists": artists,  # Use artists list, not artist_name
                        "spotify_uri": track.get("uri"),
                        "popularity": track.get("popularity", 50),
                        "audio_features": {},
                        "confidence": 0.85,  # High confidence - same artist as user mentioned
                        "confidence_score": 0.85,  # FIXED: Also set confidence_score for proper sorting
                        "source": "anchor_track",  # CRITICAL: Mark as anchor track
                        "user_mentioned": False,  # This is not a user-mentioned track itself
                        "user_mentioned_artist": True,  # CRITICAL: This is from a user-mentioned ARTIST
                        "protected": True,  # CRITICAL: Protect from filtering
                        "anchor_type": "user"  # Mark as user anchor
                    })

                    logger.debug(
                        f"Added track from user-mentioned artist: '{track.get('name')}' by {', '.join(artists)}"
                    )
            except Exception as e:
                logger.error(f"Error getting tracks for artist {artist_id}: {e}")
                continue

        if skipped_duplicates > 0:
            logger.info(f"Skipped {skipped_duplicates} duplicate tracks that were already user-mentioned")

        return recommendations

    async def _get_top_tracks_from_artists(
        self,
        artist_names: List[str],
        access_token: str,
        limit: int,
        temporal_context: Optional[Dict[str, Any]] = None,
        exclude_track_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """Get top tracks from user-mentioned artists.

        Args:
            artist_names: List of artist names mentioned by user
            access_token: Spotify access token
            limit: Maximum number of tracks to return
            temporal_context: Temporal context for filtering
            exclude_track_ids: Set of track IDs to exclude (to prevent duplicates)

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        try:
            tracks_per_artist = max(2, limit // len(artist_names)) if artist_names else limit

            # Search for all artists and prefetch their top tracks
            artist_id_map, prefetched_top_tracks_map = await self._search_and_prefetch_artists(
                artist_names, access_token
            )

            # Process artists sequentially but use prefetched data
            for artist_name in artist_names:
                try:
                    artist_id = artist_id_map.get(artist_name)
                    if not artist_id:
                        logger.warning(f"Could not find artist '{artist_name}' on Spotify")
                        continue
                    
                    # Get prefetched tracks for this artist
                    prefetched_tracks = prefetched_top_tracks_map.get(artist_id)
                    
                    artist_recs = await self._get_tracks_for_single_artist(
                        artist_name,
                        access_token,
                        tracks_per_artist,
                        temporal_context,
                        exclude_track_ids=exclude_track_ids,
                        prefetched_top_tracks=prefetched_tracks,
                        artist_id=artist_id
                    )
                    recommendations.extend(artist_recs)

                except Exception as e:
                    logger.error(f"Error getting top tracks for user-mentioned artist '{artist_name}': {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error in _get_top_tracks_from_artists: {e}", exc_info=True)

        return recommendations[:limit]

    async def _search_and_prefetch_artists(
        self,
        artist_names: List[str],
        access_token: str
    ) -> Tuple[Dict[str, str], Dict[str, List[Dict[str, Any]]]]:
        """Search for artists and prefetch their top tracks in parallel.
        
        Args:
            artist_names: List of artist names to search for
            access_token: Spotify access token
            
        Returns:
            Tuple of (artist_id_map, prefetched_top_tracks_map)
        """
        # First, search for all artists and get their IDs
        artist_id_map = {}  # Maps artist_name -> artist_id
        artist_search_tasks = []
        for artist_name in artist_names:
            async def search_artist(name: str):
                try:
                    results = await self.spotify_service.search_spotify_artists(
                        access_token=access_token,
                        query=name,
                        limit=3
                    )
                    if results:
                        artist = self._find_best_matching_artist(results, name)
                        return name, artist.get("id")
                except Exception as e:
                    logger.warning(f"Failed to search for artist '{name}': {e}")
                return name, None
            artist_search_tasks.append(search_artist(artist_name))
        
        # Search all artists in parallel
        search_results = await asyncio.gather(*artist_search_tasks, return_exceptions=True)
        for result in search_results:
            if isinstance(result, tuple):
                name, artist_id = result
                if artist_id:
                    artist_id_map[name] = artist_id
        
        # Batch prefetch top tracks for all found artists
        artist_ids = list(artist_id_map.values())
        prefetched_top_tracks_map = {}
        if artist_ids:
            prefetched_top_tracks_map = await self.spotify_service.get_artist_top_tracks_batch(
                access_token=access_token,
                artist_ids=artist_ids,
                max_concurrency=config.artist_top_tracks_max_concurrency,
            )
        
        return artist_id_map, prefetched_top_tracks_map

    async def _get_tracks_for_single_artist(
        self,
        artist_name: str,
        access_token: str,
        tracks_per_artist: int,
        temporal_context: Optional[Dict[str, Any]] = None,
        exclude_track_ids: Optional[set] = None,
        prefetched_top_tracks: Optional[List[Dict[str, Any]]] = None,
        artist_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get top tracks for a single artist by name.

        Args:
            artist_name: Name of the artist
            access_token: Spotify access token
            tracks_per_artist: Number of tracks to fetch
            temporal_context: Temporal context for filtering
            exclude_track_ids: Set of track IDs to exclude (to prevent duplicates)

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        exclude_track_ids = exclude_track_ids or set()

        # Use provided artist_id if available, otherwise search for it
        if not artist_id:
            # Search for the artist (get 3 results to find best match)
            artist_results = await self.spotify_service.search_spotify_artists(
                access_token=access_token,
                query=artist_name,
                limit=3
            )

            if not artist_results or len(artist_results) == 0:
                logger.warning(f"Could not find artist '{artist_name}' on Spotify (search returned empty)")
                return []

            # Find the best matching artist
            artist = self._find_best_matching_artist(artist_results, artist_name)
            artist_id = artist.get("id")
            if not artist_id:
                logger.warning(f"Found artist '{artist_name}' in search but no artist ID available")
                return []

        # Get artist's tracks using hybrid strategy favoring top tracks
        # Users explicitly mentioned this artist, so favor their popular/recognizable tracks
        # Use prefetched tracks if available to avoid individual API calls
        top_tracks = await self.spotify_service.get_artist_hybrid_tracks(
            artist_id=artist_id,
            access_token=access_token,
            max_popularity=95,  # Allow popular tracks (users want hits from mentioned artists)
            min_popularity=30,  # Ensure decent quality
            target_count=tracks_per_artist,
            top_tracks_ratio=0.7,  # Popular-focused: 70% top tracks, 30% album tracks
            prefetched_top_tracks=prefetched_top_tracks
        )

        # Process tracks and create recommendations
        track_count, filtered_count, skipped_duplicates = await self._process_artist_tracks(
            top_tracks, artist_name, temporal_context, exclude_track_ids, recommendations
        )

        logger.info(
            f"✓ Got {track_count} top tracks from user-mentioned artist: {artist_name} "
            f"(filtered {filtered_count}, skipped {skipped_duplicates} duplicates, marked as source='anchor_track', protected=True)"
        )

        return recommendations

    async def _process_artist_tracks(
        self,
        top_tracks: List[Dict[str, Any]],
        artist_name: str,
        temporal_context: Optional[Dict[str, Any]],
        exclude_track_ids: set,
        recommendations: List[Dict[str, Any]]
    ) -> Tuple[int, int, int]:
        """Process artist tracks and add them to recommendations.
        
        Args:
            top_tracks: List of track dictionaries from the artist
            artist_name: Name of the artist (for logging)
            temporal_context: Temporal context for filtering
            exclude_track_ids: Set of track IDs to exclude
            recommendations: List to append recommendations to
            
        Returns:
            Tuple of (track_count, filtered_count, skipped_duplicates)
        """
        track_count = 0
        filtered_count = 0
        skipped_duplicates = 0
        
        for track in top_tracks:
            if not track.get("id"):
                continue

            # Skip if this track was already added
            if track["id"] in exclude_track_ids:
                skipped_duplicates += 1
                logger.debug(
                    f"Skipping duplicate track: '{track.get('name')}' (already added)"
                )
                continue

            # CRITICAL: Apply temporal filtering BEFORE marking as protected
            is_temporal_match, temporal_reason = self._check_temporal_match(track, temporal_context)
            if not is_temporal_match:
                artists = [a.get("name", "") for a in track.get("artists", [])]
                logger.info(
                    f"✗ Filtered user-mentioned artist track '{track.get('name')}' "
                    f"by {', '.join(artists)}: {temporal_reason}"
                )
                filtered_count += 1
                continue

            # Extract all artists for consistency with other recommendation formats
            artists = [a.get("name", "") for a in track.get("artists", [])]

            recommendations.append({
                "track_id": track["id"],
                "track_name": track.get("name", ""),
                "artists": artists,  # Use artists list for consistency
                "spotify_uri": track.get("uri"),
                "popularity": track.get("popularity", 50),
                "audio_features": {},
                "confidence": 0.85,  # Very high confidence for top tracks from mentioned artists
                "confidence_score": 0.85,  # FIXED: Also set confidence_score for proper sorting
                "source": "anchor_track",  # CRITICAL: Mark as anchor track
                "user_mentioned": False,  # This is not a user-mentioned track itself
                "user_mentioned_artist": True,  # CRITICAL: This is from a user-mentioned ARTIST
                "protected": True,  # CRITICAL: Protect from filtering
                "anchor_type": "user"  # Mark as user anchor
            })
            track_count += 1
        
        return track_count, filtered_count, skipped_duplicates

    def _find_best_matching_artist(
        self,
        artist_results: List[Dict[str, Any]],
        search_name: str
    ) -> Dict[str, Any]:
        """Find the best matching artist from search results.

        Args:
            artist_results: List of artist dictionaries from Spotify search
            search_name: Original artist name searched for

        Returns:
            Best matching artist dictionary
        """
        # Find the first artist whose name actually matches what we searched for
        matched_artist = None
        for artist_candidate in artist_results:
            candidate_name = artist_candidate.get("name", "").lower()
            search_name_lower = search_name.lower()
            
            # Check if names match (exact or very close)
            if candidate_name == search_name_lower or search_name_lower in candidate_name or candidate_name in search_name_lower:
                matched_artist = artist_candidate
                break
        
        # If no match found, fall back to first result
        artist = matched_artist if matched_artist else artist_results[0]
        artist_name_from_spotify = artist.get("name", "Unknown")
        artist_id = artist.get("id")
        
        # Log what Spotify actually returned
        if matched_artist:
            logger.info(
                f"✓ Spotify search for '{search_name}' matched: "
                f"'{artist_name_from_spotify}' (ID: {artist_id})"
            )
        else:
            logger.warning(
                f"Spotify search for '{search_name}' returned unmatched: "
                f"'{artist_name_from_spotify}' (ID: {artist_id}) - using anyway"
            )
        
        return artist
