"""Seed-based recommendation generator."""

import asyncio
import structlog
from typing import Any, Dict, List, Optional

from ....states.agent_state import AgentState, TrackRecommendation
from ....tools.reccobeat_service import RecoBeatService
from ...utils.config import config
from ..handlers.audio_features import AudioFeaturesHandler
from ..handlers.track_filter import TrackFilter
from ..handlers.scoring import ScoringEngine

logger = structlog.get_logger(__name__)


class SeedBasedGenerator:
    """Generates recommendations from seed tracks using RecoBeat API."""

    def __init__(self, reccobeat_service: RecoBeatService):
        """Initialize the seed-based generator.

        Args:
            reccobeat_service: Service for RecoBeat API operations
        """
        self.reccobeat_service = reccobeat_service
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.track_filter = TrackFilter()
        self.scoring_engine = ScoringEngine()

    async def generate_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from seed tracks.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from seed tracks
        """
        # Prepare seed generation parameters
        seed_chunks, reccobeat_params = self._prepare_params(state)

        # Process all seed chunks
        all_recommendations = await self._process_seed_chunks(seed_chunks, reccobeat_params, state)

        # Apply validation pass to filter out irrelevant tracks
        validated_recommendations = self._validate_recommendations(all_recommendations, state)

        logger.info(f"Generated {len(validated_recommendations)} validated recommendations from seeds")

        return [rec.dict() for rec in validated_recommendations]

    def _prepare_params(self, state: AgentState) -> tuple[List[List[str]], Dict[str, Any]]:
        """Prepare parameters for seed-based generation.

        Args:
            state: Current agent state

        Returns:
            Tuple of (seed_chunks, reccobeat_params)
        """
        # Deduplicate seeds before processing
        unique_seeds = list(dict.fromkeys(state.seed_tracks))
        if len(unique_seeds) < len(state.seed_tracks):
            logger.info(f"Deduplicated seeds: {len(state.seed_tracks)} -> {len(unique_seeds)}")

        # Split seeds into smaller chunks for multiple API calls
        seed_chunks = self._chunk_seeds(unique_seeds, chunk_size=config.seed_chunk_size)

        # Get seed target (15% of total playlist target)
        target_seed_recs = state.metadata.get("_temp_seed_target", 1)

        # Request more per chunk to account for filtering
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

        # Process chunks in parallel with bounded concurrency for better performance
        async def process_chunk_with_delay(idx: int, chunk: List[str]) -> List[TrackRecommendation]:
            """Process a chunk - removed artificial delays for better performance."""
            try:
                return await self._process_chunk(chunk, reccobeat_params, state)
            except Exception as e:
                logger.error(f"Error generating recommendations for seed chunk {chunk}: {e}")
                return []
        
        # Process chunks with controlled concurrency
        chunk_tasks = [
            process_chunk_with_delay(idx, chunk)
            for idx, chunk in enumerate(seed_chunks)
        ]
        
        # Increase concurrency while respecting RecoBeat rate limits
        semaphore = asyncio.Semaphore(10)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        chunk_results = await asyncio.gather(*[bounded_task(task) for task in chunk_tasks])
        
        for chunk_recommendations in chunk_results:
            all_recommendations.extend(chunk_recommendations)

        logger.info(f"Generated {len(all_recommendations)} raw recommendations from {len(seed_chunks)} seed chunks")
        return all_recommendations

    async def _process_chunk(
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
        # Get recommendations for this seed chunk (ONLY use seeds, negative_seeds, and size)
        chunk_recommendations = await self.reccobeat_service.get_track_recommendations(
            seeds=chunk,
            size=self._per_chunk_size,
            **reccobeat_params
        )

        # Collect track IDs and kick off detail/audio feature fetches in parallel
        track_data = []
        track_ids = []
        for rec_data in chunk_recommendations:
            track_id = rec_data.get("track_id", "")
            if track_id:
                track_ids.append(track_id)
                track_data.append((track_id, rec_data.get("audio_features")))

        audio_features_task = asyncio.create_task(
            self.audio_features_handler.get_batch_complete_audio_features(track_data)
        )
        track_details_task = asyncio.create_task(
            self.reccobeat_service.get_tracks_by_ids(track_ids)
        )

        audio_features_map, track_details = await asyncio.gather(
            audio_features_task,
            track_details_task,
        )

        track_details_map = {
            detail.get("id"): detail
            for detail in track_details
            if detail.get("id")
        }

        # Convert to TrackRecommendation objects
        recommendations = []
        for rec_data in chunk_recommendations:
            try:
                recommendation = await self._create_recommendation(
                    rec_data,
                    chunk,
                    state,
                    audio_features_map,
                    track_details_map,
                )
                if recommendation:
                    recommendations.append(recommendation)

            except Exception as e:
                logger.warning(f"Failed to create recommendation object: {e}")
                continue

        return recommendations

    async def _create_recommendation(
        self,
        rec_data: Dict[str, Any],
        chunk: List[str],
        state: AgentState,
        audio_features_map: Dict[str, Dict[str, Any]],
        track_details_map: Dict[str, Dict[str, Any]],
    ) -> Optional[TrackRecommendation]:
        """Create a recommendation from seed-based RecoBeat data.

        Args:
            rec_data: Recommendation data from RecoBeat
            chunk: Original seed chunk
            state: Current agent state
            audio_features_map: Pre-fetched audio features for all tracks
            track_details_map: Detailed track metadata fetched in parallel

        Returns:
            TrackRecommendation object or None if invalid
        """
        track_id = rec_data.get("track_id", "")
        if not track_id:
            logger.warning("Skipping recommendation without track ID")
            return None

        # Get audio features from pre-fetched batch
        complete_audio_features = dict(audio_features_map.get(track_id, {}))

        track_details = track_details_map.get(track_id)
        if track_details:
            duration_from_details = (
                track_details.get("duration_ms")
                or track_details.get("durationMs")
            )
            if duration_from_details and "duration_ms" not in complete_audio_features:
                complete_audio_features["duration_ms"] = duration_from_details

            popularity_from_details = track_details.get("popularity")
            if (
                popularity_from_details is not None
                and "popularity" not in complete_audio_features
            ):
                complete_audio_features["popularity"] = popularity_from_details

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

    def _validate_recommendations(
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
                logger.info(
                    f"Filtered out invalid track from seeds: {rec.track_name} "
                    f"by {', '.join(rec.artists)} - {reason}"
                )

        logger.info(
            f"Validation pass: {len(recommendations)} -> {len(validated_recommendations)} tracks "
            f"(filtered {len(recommendations) - len(validated_recommendations)})"
        )

        return validated_recommendations

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
            if len(chunk) > 0:
                chunks.append(chunk)
        return chunks
