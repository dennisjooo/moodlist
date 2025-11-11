"""Playlist ordering agent for creating energy flow arcs."""

import asyncio
import structlog
from typing import Any, Dict, List

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, TrackRecommendation, RecommendationStatus
from ..utils.config import config
from ..utils.llm_response_parser import LLMResponseParser
from ..utils.track_deduplicator import deduplicate_track_recommendations
from .prompts import (
    get_track_energy_analysis_system_prompt,
    get_track_energy_analysis_user_prompt,
    get_ordering_strategy_system_prompt,
    get_ordering_strategy_user_prompt,
)
from .phase_assigner import PhaseAssigner
from .phase_sorter import PhaseSorter
from .energy_analyzer import EnergyAnalyzer
from .strategy_builder import StrategyBuilder

logger = structlog.get_logger(__name__)


class PlaylistOrderingAgent(BaseAgent):
    """Agent for ordering playlist tracks based on energy flow and listening experience."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        verbose: bool = False
    ):
        """Initialize the playlist ordering agent.

        Args:
            llm: Language model for analysis
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="PlaylistOrderingAgent",
            description="Orders playlist tracks to create optimal energy flow and listening experience",
            llm=llm,
            verbose=verbose
        )
        
        # Initialize components
        self.phase_assigner = PhaseAssigner()
        self.phase_sorter = PhaseSorter()
        self.energy_analyzer = EnergyAnalyzer()
        self.strategy_builder = StrategyBuilder()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute playlist ordering.

        Args:
            state: Current agent state with recommendations

        Returns:
            Updated agent state with ordered recommendations
        """
        try:
            logger.info(f"Starting playlist ordering for session {state.session_id}")
            state.status = RecommendationStatus.OPTIMIZING_RECOMMENDATIONS
            state.current_step = "ordering_playlist"

            if not state.recommendations:
                logger.warning("No recommendations to order")
                return state

            if len(state.recommendations) < 3:
                logger.info(f"Only {len(state.recommendations)} tracks - skipping ordering")
                return state

            # CRITICAL: Remove any duplicates that somehow made it through
            # This is a safety measure to ensure clean input for ordering
            original_count = len(state.recommendations)
            state.recommendations = self._remove_duplicates(state.recommendations)
            if len(state.recommendations) < original_count:
                logger.warning(
                    f"Found and removed {original_count - len(state.recommendations)} duplicate tracks "
                    f"before ordering (this should not happen - duplicates should be removed earlier)"
                )

            # Step 1: Analyze track energy characteristics and attach to recommendations
            track_analyses = await self._analyze_track_energies(state)
            self._attach_energy_analyses_to_tracks(state.recommendations, track_analyses)

            # Step 2: Determine optimal ordering strategy
            strategy = await self._determine_ordering_strategy(state, track_analyses)

            # Step 3: Order tracks according to strategy
            ordered_recommendations = self._order_tracks(
                state.recommendations,
                track_analyses,
                strategy
            )

            # Update state with ordered recommendations
            state.recommendations = ordered_recommendations

            # Store ordering metadata
            state.metadata["ordering_strategy"] = strategy
            state.metadata["ordering_applied"] = True

            logger.info(
                "Playlist ordering complete",
                strategy=strategy.get("strategy"),
                track_count=len(ordered_recommendations)
            )

            return state

        except Exception as e:
            logger.error(f"Error in playlist ordering: {e}", exc_info=True)
            # Don't fail the entire workflow - return original order
            state.metadata["ordering_error"] = str(e)
            state.metadata["ordering_applied"] = False
            return state

    async def _analyze_track_energies(self, state: AgentState) -> List[Dict[str, Any]]:
        """Analyze energy characteristics of all tracks in batches.

        Args:
            state: Current agent state

        Returns:
            List of track energy analyses
        """
        batch_size = config.track_energy_analysis_batch_size
        logger.info(f"Analyzing energy characteristics for {len(state.recommendations)} tracks in batches of {batch_size}")

        # Split tracks into batches
        batches = [
            state.recommendations[i:i + batch_size]
            for i in range(0, len(state.recommendations), batch_size)
        ]

        # Analyze batches in parallel
        try:
            total_batches = len(batches)
            batch_tasks = [
                self._analyze_track_batch_with_timeout(
                    batch_index=i,
                    total_batches=total_batches,
                    tracks=batch,
                    mood_prompt=state.mood_prompt
                )
                for i, batch in enumerate(batches)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Combine results from all batches
            all_analyses = []
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing batch {i+1}: {result}")
                    # Use fallback for failed batch
                    all_analyses.extend(self.energy_analyzer.analyze_from_audio_features(batches[i]))
                else:
                    all_analyses.extend(result)

            logger.info(f"Successfully analyzed {len(all_analyses)} tracks across {len(batches)} batches")
            return all_analyses

        except Exception as e:
            logger.error(f"Error in batch analysis: {e}", exc_info=True)
            return self.energy_analyzer.analyze_from_audio_features(state.recommendations)

    async def _analyze_track_batch(
        self,
        tracks: List[TrackRecommendation],
        mood_prompt: str
    ) -> List[Dict[str, Any]]:
        """Analyze a single batch of tracks.

        Args:
            tracks: Batch of track recommendations
            mood_prompt: User's mood prompt for context

        Returns:
            List of track energy analyses for this batch
        """
        # Prepare track information for analysis
        tracks_info = [
            {
                "track_id": rec.track_id,
                "track_name": f"{rec.track_name} - {rec.artists[0] if rec.artists else 'Unknown'}",
                "audio_features": rec.audio_features or {}
            }
            for rec in tracks
        ]

        # Create analysis prompts
        system_prompt = get_track_energy_analysis_system_prompt()
        user_prompt = get_track_energy_analysis_user_prompt(mood_prompt, tracks_info)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)

        # Parse JSON response using utility
        analysis_result = LLMResponseParser.extract_json_from_response(
            response,
            fallback={"track_analyses": []}
        )
        return analysis_result.get("track_analyses", [])

    async def _analyze_track_batch_with_timeout(
        self,
        batch_index: int,
        total_batches: int,
        tracks: List[TrackRecommendation],
        mood_prompt: str
    ) -> List[Dict[str, Any]]:
        """Run batch analysis with timeout and automatic fallbacks."""
        timeout = config.track_energy_analysis_timeout_seconds
        batch_label = f"{batch_index + 1}/{total_batches}"
        logger.debug(
            "Starting energy analysis batch",
            batch=batch_label,
            track_count=len(tracks)
        )

        try:
            result = await asyncio.wait_for(
                self._analyze_track_batch(tracks, mood_prompt),
                timeout=timeout
            )
            result = self._ensure_complete_batch_analysis(tracks, result, batch_label)
            logger.info(
                "Completed energy analysis batch",
                batch=batch_label,
                analyzed_tracks=len(result)
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(
                "Energy analysis batch timed out, falling back to audio features",
                batch=batch_label,
                timeout_seconds=timeout,
                track_count=len(tracks)
            )
            return self.energy_analyzer.analyze_from_audio_features(tracks)

        except Exception as exc:
            logger.error(
                "Energy analysis batch failed, falling back to audio features",
                batch=batch_label,
                error=str(exc),
                track_count=len(tracks)
            )
            return self.energy_analyzer.analyze_from_audio_features(tracks)

    def _ensure_complete_batch_analysis(
        self,
        tracks: List[TrackRecommendation],
        analyses: List[Dict[str, Any]],
        batch_label: str
    ) -> List[Dict[str, Any]]:
        """Ensure each track in the batch has an analysis entry."""
        provided_ids = {
            analysis.get("track_id")
            for analysis in analyses
            if analysis.get("track_id")
        }
        missing_tracks = [
            rec for rec in tracks
            if rec.track_id not in provided_ids
        ]

        if missing_tracks:
            logger.warning(
                "Energy analysis batch missing tracks, supplementing from audio features",
                batch=batch_label,
                missing_count=len(missing_tracks),
                analyzed_count=len(analyses)
            )
            analyses.extend(self.energy_analyzer.analyze_from_audio_features(missing_tracks))

        return analyses

    def _attach_energy_analyses_to_tracks(
        self,
        recommendations: List[TrackRecommendation],
        track_analyses: List[Dict[str, Any]]
    ) -> None:
        """Attach energy analyses directly to track recommendations.

        Args:
            recommendations: List of track recommendations
            track_analyses: List of energy analyses
        """
        # Create mapping of track_id to analysis
        analysis_map = {a["track_id"]: a for a in track_analyses}

        # Attach analysis to each track
        for rec in recommendations:
            if rec.track_id in analysis_map:
                rec.energy_analysis = analysis_map[rec.track_id]
                logger.debug(f"Attached energy analysis to track {rec.track_id}")

        logger.info(f"Attached energy analyses to {len([r for r in recommendations if r.energy_analysis])} tracks")

    async def _determine_ordering_strategy(
        self,
        state: AgentState,
        track_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine the optimal ordering strategy for the playlist.

        Args:
            state: Current agent state
            track_analyses: Track energy analyses

        Returns:
            Ordering strategy
        """
        logger.info("Determining optimal ordering strategy")

        # Calculate aggregate statistics
        avg_energy = sum(t.get("energy_level", 50) for t in track_analyses) / len(track_analyses)
        max_energy = max(t.get("energy_level", 50) for t in track_analyses)
        min_energy = min(t.get("energy_level", 50) for t in track_analyses)
        energy_range = max_energy - min_energy
        user_mentioned_count = len([t for t in state.metadata.get('anchor_tracks', []) if t.get('user_mentioned', False)])

        # Create strategy prompts
        system_prompt = get_ordering_strategy_system_prompt()
        user_prompt = get_ordering_strategy_user_prompt(
            mood_prompt=state.mood_prompt,
            track_count=len(state.recommendations),
            avg_energy=avg_energy,
            max_energy=max_energy,
            min_energy=min_energy,
            energy_range=energy_range,
            track_analyses=track_analyses,
            user_mentioned_count=user_mentioned_count
        )

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse JSON response using utility
            strategy = LLMResponseParser.extract_json_from_response(response)
            logger.info(f"Selected strategy: {strategy.get('strategy')}")
            return strategy

        except Exception as e:
            logger.error(f"Error determining strategy: {e}", exc_info=True)
            # Return default strategy
            return self.strategy_builder.build_default_strategy(avg_energy, energy_range, len(track_analyses))

    def _order_tracks(
        self,
        recommendations: List[TrackRecommendation],
        track_analyses: List[Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> List[TrackRecommendation]:
        """Order tracks according to the determined strategy.

        Args:
            recommendations: Original recommendations
            track_analyses: Track energy analyses
            strategy: Ordering strategy

        Returns:
            Ordered list of recommendations
        """
        logger.info("Ordering tracks according to strategy")

        # Create a mapping of track_id to analysis
        analysis_map = {a["track_id"]: a for a in track_analyses}

        # Assign tracks to phases based on their characteristics
        phase_buckets = self.phase_assigner.assign_tracks_to_phases(
            recommendations,
            analysis_map,
            strategy
        )

        # Order tracks within each phase
        ordered_recommendations = []
        phase_order = self.phase_assigner.phase_order

        for phase in phase_order:
            phase_tracks = phase_buckets.get(phase, [])
            if phase_tracks:
                # Sort within phase for smooth transitions
                sorted_phase = self.phase_sorter.sort_tracks_within_phase(
                    phase_tracks, analysis_map, phase
                )
                ordered_recommendations.extend(sorted_phase)
                logger.info(f"Phase '{phase}': {len(sorted_phase)} tracks")

        return ordered_recommendations

    def _remove_duplicates(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Remove duplicate tracks from recommendations.

        Args:
            recommendations: List of track recommendations

        Returns:
            List with duplicates removed, preserving order and keeping first occurrence
        """
        unique_recommendations, _ = deduplicate_track_recommendations(
            recommendations,
            on_duplicate=lambda rec: logger.debug(
                "duplicate_found_ordering_agent",
                track_id=rec.track_id,
                track_name=rec.track_name,
                artists=rec.artists,
            ),
        )
        return unique_recommendations
