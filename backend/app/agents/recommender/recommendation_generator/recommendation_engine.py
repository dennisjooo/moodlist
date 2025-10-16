"""Recommendation generation engine."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ...tools.reccobeat_service import RecoBeatService
from ...tools.spotify_service import SpotifyService
from ...states.agent_state import AgentState, TrackRecommendation
from .token_manager import TokenManager
from .audio_features import AudioFeaturesHandler
from .track_filter import TrackFilter
from .scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Engine for generating track recommendations from various sources."""

    def __init__(self, reccobeat_service: RecoBeatService, spotify_service: SpotifyService):
        """Initialize the recommendation engine.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
        """
        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service

        # Initialize supporting components
        self.token_manager = TokenManager()
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.track_filter = TrackFilter()
        self.scoring_engine = ScoringEngine()

    async def _generate_mood_based_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations based on mood analysis, seeds, and discovered artists.

        Target ratio: 95:5 (95% from artist discovery, 5% from seed-based recommendations).
        Artist discovery is overwhelmingly prioritized as RecoBeat recommendations tend to be lower quality.

        RecoBeat API calls use ONLY seeds, negative_seeds, and size parameters.
        Audio feature parameters are NOT used as they cause RecoBeat to return irrelevant tracks.

        Args:
            state: Current agent state

        Returns:
            List of raw recommendations (mostly from artist discovery)
        """
        all_recommendations = []

        # Get target to calculate desired split
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)

        # Calculate target split: 95:5 ratio (95% artists, 5% seeds)
        target_artist_recs = int(target_count * 0.95)  # 95% from artists
        target_seed_recs = target_count - target_artist_recs  # 5% from seeds

        # Store targets in state for use by generation methods
        state.metadata["_temp_seed_target"] = target_seed_recs
        state.metadata["_temp_artist_target"] = target_artist_recs

        logger.info(
            f"Target generation split (95:5 ratio): {target_artist_recs} from artists, "
            f"{target_seed_recs} from seeds (total: {target_count})"
        )

        # Generate from discovered artists FIRST (aiming for 2/3 of target - higher priority)
        artist_recommendations = await self._generate_from_discovered_artists(state)
        all_recommendations.extend(artist_recommendations)

        # Generate from seed tracks (aiming for 1/3 of target - supplement only)
        seed_recommendations = await self._generate_from_seeds(state)
        all_recommendations.extend(seed_recommendations)

        # Clean up temp metadata
        state.metadata.pop("_temp_seed_target", None)
        state.metadata.pop("_temp_artist_target", None)

        logger.info(
            f"Generated {len(all_recommendations)} total recommendations "
            f"({len(artist_recommendations)} from artists [{target_artist_recs} target], "
            f"{len(seed_recommendations)} from seeds [{target_seed_recs} target])"
        )

        return all_recommendations

    async def _generate_from_seeds(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from seed tracks.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from seed tracks
        """
        # Prepare seed generation parameters
        seed_chunks, reccobeat_params = self._prepare_seed_generation_params(state)

        # Process all seed chunks
        all_recommendations = await self._process_seed_chunks(seed_chunks, reccobeat_params, state)

        # Apply validation pass to filter out irrelevant tracks
        validated_recommendations = self._validate_seed_recommendations(all_recommendations, state)

        logger.info(f"Generated {len(validated_recommendations)} validated recommendations from seeds")

        return [rec.dict() for rec in validated_recommendations]

    def _prepare_seed_generation_params(self, state: AgentState) -> tuple[List[List[str]], Dict[str, Any]]:
        """Prepare parameters for seed-based generation.

        Args:
            state: Current agent state

        Returns:
            Tuple of (seed_chunks, reccobeat_params)
        """
        # Deduplicate seeds before processing
        unique_seeds = list(dict.fromkeys(state.seed_tracks))  # Preserves order
        if len(unique_seeds) < len(state.seed_tracks):
            logger.info(f"Deduplicated seeds: {len(state.seed_tracks)} -> {len(unique_seeds)}")

        # Split seeds into smaller chunks for multiple API calls
        seed_chunks = self._chunk_seeds(unique_seeds, chunk_size=3)

        # Get seed target (5% of total playlist target - very minimal supplementary)
        target_seed_recs = state.metadata.get("_temp_seed_target", 1)  # Default ~5% of 20

        # Request more per chunk to account for filtering (aim for 2x target due to low count)
        per_chunk_size = min(10, max(int((target_seed_recs * 2) // len(seed_chunks)) + 2, 3))

        # Store per_chunk_size for use in processing
        self._per_chunk_size = per_chunk_size

        # Prepare minimal RecoBeat params (NO audio features - they cause issues)
        reccobeat_params = {}

        # Add negative seeds if available (limit to 5 as per RecoBeat API)
        if state.negative_seeds:
            reccobeat_params["negative_seeds"] = state.negative_seeds[:5]
            logger.info(f"Using {len(reccobeat_params['negative_seeds'])} negative seeds to avoid similar tracks")

        return seed_chunks, reccobeat_params

    async def _process_seed_chunks(
        self,
        seed_chunks: List[List[str]],
        reccobeat_params: Dict[str, Any],
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Process all seed chunks to get recommendations.

        Args:
            seed_chunks: List of seed track ID chunks
            reccobeat_params: Parameters for RecoBeat API
            state: Current agent state

        Returns:
            List of TrackRecommendation objects
        """
        all_recommendations = []

        for chunk in seed_chunks:
            try:
                chunk_recommendations = await self._process_seed_chunk(chunk, reccobeat_params, state)
                all_recommendations.extend(chunk_recommendations)

                # Add some delay between API calls to respect rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating recommendations for seed chunk {chunk}: {e}")
                continue

        logger.info(f"Generated {len(all_recommendations)} raw recommendations from {len(seed_chunks)} seed chunks")
        return all_recommendations

    async def _process_seed_chunk(
        self,
        chunk: List[str],
        reccobeat_params: Dict[str, Any],
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Process a single seed chunk.

        Args:
            chunk: List of seed track IDs
            reccobeat_params: Parameters for RecoBeat API
            state: Current agent state

        Returns:
            List of TrackRecommendation objects from this chunk
        """
        # Get recommendations for this seed chunk
        # ONLY use seeds, negative_seeds, and size - NO audio feature params
        chunk_recommendations = await self.reccobeat_service.get_track_recommendations(
            seeds=chunk,
            size=self._per_chunk_size,
            **reccobeat_params
        )

        # Convert to TrackRecommendation objects
        recommendations = []
        for rec_data in chunk_recommendations:
            try:
                recommendation = await self._create_seed_recommendation(rec_data, chunk, state)
                if recommendation:
                    recommendations.append(recommendation)

            except Exception as e:
                logger.warning(f"Failed to create recommendation object: {e}")
                continue

        return recommendations

    async def _create_seed_recommendation(
        self,
        rec_data: Dict[str, Any],
        chunk: List[str],
        state: AgentState
    ) -> Optional[TrackRecommendation]:
        """Create a recommendation from seed-based RecoBeat data.

        Args:
            rec_data: Recommendation data from RecoBeat
            chunk: Original seed chunk
            state: Current agent state

        Returns:
            TrackRecommendation object or None if invalid
        """
        track_id = rec_data.get("track_id", "")
        if not track_id:
            logger.warning("Skipping recommendation without track ID")
            return None

        # Get complete audio features for this track
        complete_audio_features = await self.audio_features_handler.get_complete_audio_features(
            track_id, rec_data.get("audio_features")
        )

        # Use confidence score from RecoBeat if available, otherwise calculate
        confidence = rec_data.get("confidence_score")
        if confidence is None:
            confidence = self.scoring_engine.calculate_confidence_score(rec_data, state)

        return TrackRecommendation(
            track_id=track_id,
            track_name=rec_data.get("track_name", "Unknown Track"),
            artists=rec_data.get("artists", ["Unknown Artist"]),
            spotify_uri=rec_data.get("spotify_uri"),
            confidence_score=confidence,
            audio_features=complete_audio_features,
            reasoning=rec_data.get("reasoning", f"Mood-based recommendation using seeds: {', '.join(chunk)}"),
            source=rec_data.get("source", "reccobeat")
        )

    def _validate_seed_recommendations(
        self,
        recommendations: List[TrackRecommendation],
        state: AgentState
    ) -> List[TrackRecommendation]:
        """Validate seed-based recommendations.

        Args:
            recommendations: Raw recommendations to validate
            state: Current agent state

        Returns:
            Validated recommendations
        """
        validated_recommendations = []

        for rec in recommendations:
            is_valid, reason = self.track_filter.validate_track_relevance(
                rec.track_name, rec.artists, state.mood_analysis
            )
            if is_valid:
                validated_recommendations.append(rec)
            else:
                logger.info(f"Filtered out invalid track from seeds: {rec.track_name} by {', '.join(rec.artists)} - {reason}")

        logger.info(f"Validation pass: {len(recommendations)} -> {len(validated_recommendations)} tracks (filtered {len(recommendations) - len(validated_recommendations)})")

        return validated_recommendations

    async def _generate_fallback_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when no seeds are available.

        Args:
            state: Current agent state

        Returns:
            List of fallback recommendations
        """
        logger.info("Generating fallback recommendations without seeds")

        # Use mood-based search with artist keywords
        # Support both old format (search_keywords) and new format (keywords)
        if state.mood_analysis:
            keywords = state.mood_analysis.get("keywords") or state.mood_analysis.get("search_keywords")

            if keywords:
                # Use top 3 keywords
                keywords_to_use = keywords[:3] if isinstance(keywords, list) else [keywords]

                # Search for artists matching mood keywords
                matching_artists = await self.reccobeat_service.search_artists_by_mood(
                    keywords_to_use,
                    limit=5
                )

                if matching_artists:
                    # Use found artists as seeds for recommendations
                    artist_ids = [artist["id"] for artist in matching_artists if artist.get("id")]

                    if artist_ids:
                        # Deduplicate artist IDs
                        unique_artist_ids = list(dict.fromkeys(artist_ids[:3]))
                        fallback_recommendations = await self.reccobeat_service.get_track_recommendations(
                            seeds=unique_artist_ids,
                            size=20
                            # NO audio feature params - keep it simple
                        )

                        logger.info(f"Generated {len(fallback_recommendations)} fallback recommendations using {len(artist_ids)} artists")
                        return fallback_recommendations

        # If all else fails, return empty list
        logger.warning("Could not generate fallback recommendations")
        return []

    def _chunk_seeds(self, seeds: List[str], chunk_size: int = 3) -> List[List[str]]:
        """Split seeds into smaller chunks for API calls.

        Args:
            seeds: List of seed track IDs
            chunk_size: Size of each chunk

        Returns:
            List of seed chunks
        """
        chunks = []
        for i in range(0, len(seeds), chunk_size):
            chunk = seeds[i:i + chunk_size]
            if len(chunk) > 0:  # Only add non-empty chunks
                chunks.append(chunk)
        return chunks

    def _extract_mood_features(self, state: AgentState) -> Dict[str, Any]:
        """Extract features for RecoBeat API.

        DEPRECATED: We now only use seeds and negative_seeds, no audio features.
        Audio feature parameters cause RecoBeat to return irrelevant tracks.

        Args:
            state: Current agent state with mood analysis and target features

        Returns:
            Empty dict (audio features no longer used)
        """
        logger.info("Audio features extraction skipped - using seed-based recommendations only")
        return {}

    async def _generate_from_discovered_artists(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from mood-matched artists.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from discovered artists
        """
        # Get mood-matched artists from state metadata
        mood_matched_artists = state.metadata.get("mood_matched_artists", [])

        if not mood_matched_artists:
            logger.info("No mood-matched artists available for recommendations")
            return []

        logger.info(f"Generating recommendations from {len(mood_matched_artists)} discovered artists")

        # Prepare parameters and refresh token
        access_token, target_features, tracks_per_artist = await self._prepare_artist_discovery_params(state)

        if not access_token:
            return []

        # Process all artists
        all_recommendations, successful_artists, failed_artists = await self._process_all_artists(
            mood_matched_artists, access_token, target_features, tracks_per_artist
        )

        # Handle error cases
        self._handle_artist_discovery_errors(successful_artists, failed_artists, len(mood_matched_artists))

        logger.info(
            f"Generated {len(all_recommendations)} recommendations from {successful_artists}/{min(len(mood_matched_artists), 20)} artists "
            f"({failed_artists} failed) - maximized diversity by spreading across more artists"
        )

        return [rec.dict() for rec in all_recommendations]

    async def _prepare_artist_discovery_params(self, state: AgentState) -> tuple[str, Dict[str, Any], int]:
        """Prepare parameters for artist discovery.

        Args:
            state: Current agent state

        Returns:
            Tuple of (access_token, target_features, tracks_per_artist)
        """
        # CRITICAL: Refresh Spotify token RIGHT BEFORE making API calls
        state = await self.token_manager.refresh_token_from_workflow(state)

        # Get target features for filtering
        target_features = state.metadata.get("target_features", {})

        # Get artist target (95% of total playlist target - DOMINANT source, 95:5 ratio)
        target_artist_recs = state.metadata.get("_temp_artist_target", 19)  # Default 95% of 20

        # Get access token for Spotify API (after refresh)
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.error("CRITICAL: No Spotify access token available for artist top tracks (even after refresh attempt)")
            return None, {}, 0

        logger.info(f"Using Spotify access token (length: {len(access_token)}, first 20 chars: {access_token[:20]}...)")

        # MAXIMIZE DIVERSITY: Use MORE artists with MORE tracks each to account for filtering
        artist_count = min(len(state.metadata.get("mood_matched_artists", [])), 20)
        tracks_per_artist = max(3, min(int((target_artist_recs * 2.5) // artist_count) + 2, 5))

        logger.info(
            f"MAXIMIZING DIVERSITY: Fetching {tracks_per_artist} tracks from up to {artist_count} artists "
            f"(aiming for ~{tracks_per_artist * artist_count} tracks before filtering) "
            f"to reach artist target of {target_artist_recs} tracks after filtering (95:5 ratio)"
        )

        return access_token, target_features, tracks_per_artist

    async def _process_all_artists(
        self,
        mood_matched_artists: List[str],
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int
    ) -> tuple[List[TrackRecommendation], int, int]:
        """Process all artists to get recommendations.

        Args:
            mood_matched_artists: List of artist IDs
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch per artist

        Returns:
            Tuple of (recommendations, successful_artists, failed_artists)
        """
        all_recommendations = []
        successful_artists = 0
        failed_artists = 0

        # Fetch tracks from each artist (use up to 20 artists for maximum coverage and variety)
        for idx, artist_id in enumerate(mood_matched_artists[:20]):
            try:
                artist_recommendations = await self._fetch_tracks_from_artist(
                    artist_id, idx, len(mood_matched_artists), access_token, target_features, tracks_per_artist
                )
                all_recommendations.extend(artist_recommendations)

                if artist_recommendations:  # Only count as successful if we got recommendations
                    successful_artists += 1
                else:
                    failed_artists += 1

                # Small delay between artists
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error getting tracks for artist {artist_id} (artist {idx+1}/{min(len(mood_matched_artists), 20)}): {e}", exc_info=True)
                failed_artists += 1
                continue

        return all_recommendations, successful_artists, failed_artists

    async def _fetch_tracks_from_artist(
        self,
        artist_id: str,
        artist_index: int,
        total_artists: int,
        access_token: str,
        target_features: Dict[str, Any],
        tracks_per_artist: int
    ) -> List[TrackRecommendation]:
        """Fetch and process tracks from a single artist.

        Args:
            artist_id: Spotify artist ID
            artist_index: Index of this artist in the list
            total_artists: Total number of artists
            access_token: Spotify access token
            target_features: Target mood features
            tracks_per_artist: Number of tracks to fetch

        Returns:
            List of TrackRecommendation objects from this artist
        """
        logger.info(f"Fetching top tracks for artist {artist_index+1}/{min(total_artists, 20)}: {artist_id}")

        # Get top tracks from Spotify (more reliable than RecoBeat)
        artist_tracks = await self.spotify_service.get_artist_top_tracks(
            access_token=access_token,
            artist_id=artist_id,
            market="US"
        )

        if not artist_tracks:
            logger.warning(
                f"No tracks returned for artist {artist_id} (artist {artist_index+1}/{min(total_artists, 20)}) - "
                f"This may indicate a Spotify API authentication issue or invalid artist ID"
            )
            return []

        logger.info(
            f"Successfully got {len(artist_tracks)} tracks from artist {artist_id}, "
            f"will process top {tracks_per_artist} for recommendations"
        )

        # Process tracks from this artist
        return await self._process_artist_tracks(
            artist_tracks[:tracks_per_artist], artist_id, target_features
        )

    async def _process_artist_tracks(
        self,
        artist_tracks: List[Dict[str, Any]],
        artist_id: str,
        target_features: Dict[str, Any]
    ) -> List[TrackRecommendation]:
        """Process tracks from an artist into recommendations.

        Args:
            artist_tracks: List of track data from Spotify
            artist_id: Spotify artist ID
            target_features: Target mood features

        Returns:
            List of TrackRecommendation objects
        """
        recommendations = []
        tracks_added = 0

        for track in artist_tracks:
            try:
                recommendation = await self._create_artist_track_recommendation(track, target_features)
                if recommendation:
                    recommendations.append(recommendation)
                    tracks_added += 1

            except Exception as e:
                logger.warning(f"Failed to process artist track: {e}")
                continue

        # Log how many tracks were actually added from this artist
        logger.info(
            f"Added {tracks_added}/{len(artist_tracks)} tracks from artist {artist_id} "
            f"({len(artist_tracks) - tracks_added} filtered out)"
        )

        return recommendations

    async def _create_artist_track_recommendation(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> Optional[TrackRecommendation]:
        """Create a recommendation from an artist track.

        Args:
            track: Track data from Spotify
            target_features: Target mood features

        Returns:
            TrackRecommendation object or None if filtered out
        """
        # Spotify returns tracks with 'id' key
        track_id = track.get("id")
        if not track_id:
            logger.debug(f"Skipping track without ID: {track}")
            return None

        # Get audio features
        audio_features = await self.audio_features_handler.get_complete_audio_features(track_id)

        # Score track against mood (RELAXED for artist tracks)
        cohesion_score = self._calculate_artist_track_score(audio_features, target_features)

        # Very relaxed threshold for artist tracks (0.3 vs 0.6 for RecoBeat)
        if cohesion_score < 0.3:
            logger.info(
                f"Filtering low-cohesion artist track: {track.get('name')} "
                f"(cohesion: {cohesion_score:.2f} < 0.3 threshold)"
            )
            return None

        # Create recommendation (extract artist names from Spotify format)
        artist_names = [artist.get("name", "Unknown") for artist in track.get("artists", [])]

        # Get Spotify URI - API returns 'uri' field, not 'spotify_uri'
        spotify_uri = track.get("spotify_uri") or track.get("uri")

        return TrackRecommendation(
            track_id=track_id,
            track_name=track.get("name", "Unknown Track"),
            artists=artist_names if artist_names else ["Unknown Artist"],
            spotify_uri=spotify_uri,
            confidence_score=cohesion_score,
            audio_features=audio_features,
            reasoning=f"From mood-matched artist (cohesion: {cohesion_score:.2f})",
            source="artist_discovery"
        )

    def _calculate_artist_track_score(
        self,
        audio_features: Optional[Dict[str, Any]],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for an artist track.

        Args:
            audio_features: Track audio features
            target_features: Target mood features

        Returns:
            Confidence score
        """
        if target_features and audio_features:
            return self.scoring_engine.calculate_track_cohesion(audio_features, target_features)
        else:
            return 0.75  # Higher default for artist tracks without features

    def _handle_artist_discovery_errors(
        self,
        successful_artists: int,
        failed_artists: int,
        total_artists: int
    ) -> None:
        """Handle error cases for artist discovery.

        Args:
            successful_artists: Number of successful artists
            failed_artists: Number of failed artists
            total_artists: Total number of artists attempted
        """
        total_attempted = min(total_artists, 20)

        if failed_artists > total_attempted * 0.5:  # More than 50% failed
            logger.error(
                f"CRITICAL: Artist discovery failed for {failed_artists}/{total_attempted} artists. "
                f"This may indicate an expired Spotify access token or API issue. "
                f"Only {successful_artists} artists succeeded."
            )

            # If ALL artists failed, raise an error to prevent bad recommendations
            if successful_artists == 0:
                raise Exception(
                    f"Artist discovery completely failed - all {total_attempted} artists returned no tracks. "
                    "This is likely due to an expired or invalid Spotify access token. "
                    "The workflow cannot continue without valid artist tracks."
                )
