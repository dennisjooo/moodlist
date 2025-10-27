"""Strategy for generating recommendations from seed tracks."""

import asyncio
import structlog
from typing import Any, Dict, List

from ....tools.reccobeat_service import RecoBeatService
from ....states.agent_state import AgentState
from ...utils import TrackRecommendationFactory
from ..handlers.audio_features import AudioFeaturesHandler
from ..handlers.track_filter import TrackFilter
from ..handlers.scoring import ScoringEngine
from .base_strategy import RecommendationStrategy

logger = structlog.get_logger(__name__)


class SeedBasedStrategy(RecommendationStrategy):
    """Strategy for generating recommendations from seed tracks using RecoBeat API."""

    def __init__(self, reccobeat_service: RecoBeatService):
        """Initialize the seed-based strategy.

        Args:
            reccobeat_service: Service for RecoBeat API operations
        """
        super().__init__("seed_based")
        self.reccobeat_service = reccobeat_service
        self.audio_features_handler = AudioFeaturesHandler(reccobeat_service)
        self.track_filter = TrackFilter()
        self.scoring_engine = ScoringEngine()

    async def generate_recommendations(
        self,
        state: AgentState,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate recommendations from seed tracks.

        Args:
            state: Current agent state
            target_count: Target number of recommendations to generate

        Returns:
            List of recommendation data dictionaries
        """
        # Prepare seed generation parameters
        seed_chunks, reccobeat_params = self._prepare_seed_generation_params(state, target_count)

        # Process all seed chunks
        all_recommendations = await self._process_seed_chunks(seed_chunks, reccobeat_params, state)

        # Apply validation pass to filter out irrelevant tracks
        validated_recommendations = self._validate_seed_recommendations(all_recommendations, state)

        logger.info(f"Generated {len(validated_recommendations)} validated recommendations from seeds")

        return [rec.dict() for rec in validated_recommendations]

    def _prepare_seed_generation_params(
        self,
        state: AgentState,
        target_count: int
    ) -> tuple[List[List[str]], Dict[str, Any]]:
        """Prepare parameters for seed-based generation.

        Args:
            state: Current agent state
            target_count: Target number of recommendations

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
    ) -> List[Any]:
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
    ) -> List[Any]:
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

        # Batch fetch audio features for all tracks first
        track_data = []
        for rec_data in chunk_recommendations:
            track_id = rec_data.get("track_id", "")
            if track_id:
                track_data.append((track_id, rec_data.get("audio_features")))
        
        audio_features_map = await self.audio_features_handler.get_batch_complete_audio_features(track_data)
        
        # Convert to TrackRecommendation objects
        recommendations = []
        for rec_data in chunk_recommendations:
            try:
                recommendation = await self._create_seed_recommendation(rec_data, chunk, state, audio_features_map)
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
        state: AgentState,
        audio_features_map: Dict[str, Dict[str, Any]]
    ) -> Any:
        """Create a recommendation from seed-based RecoBeat data.

        Args:
            rec_data: Recommendation data from RecoBeat
            chunk: Original seed chunk
            state: Current agent state
            audio_features_map: Pre-fetched audio features for all tracks

        Returns:
            TrackRecommendation object or None if invalid
        """
        track_id = rec_data.get("track_id", "")
        if not track_id:
            logger.warning("Skipping recommendation without track ID")
            return None

        # Get audio features from pre-fetched batch
        complete_audio_features = audio_features_map.get(track_id, {})

        # Use confidence score from RecoBeat if available, otherwise calculate
        confidence = rec_data.get("confidence_score")
        if confidence is None:
            confidence = self.scoring_engine.calculate_confidence_score(rec_data, state)

        # Enhance the data with complete audio features
        enhanced_data = rec_data.copy()
        enhanced_data["audio_features"] = complete_audio_features
        enhanced_data["confidence_score"] = confidence

        return TrackRecommendationFactory.from_seed_based_generation(
            response_data=enhanced_data,
            seed_tracks=chunk,
            reasoning=rec_data.get("reasoning", f"Mood-based recommendation using seeds: {', '.join(chunk)}")
        )

    def _validate_seed_recommendations(
        self,
        recommendations: List[Any],
        state: AgentState
    ) -> List[Any]:
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
