"""Playlist ordering agent for creating energy flow arcs."""

import asyncio
import structlog
from typing import Any, Dict, List

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage

from ...core.base_agent import BaseAgent
from ...states.agent_state import AgentState, TrackRecommendation, RecommendationStatus
from ..utils.llm_response_parser import LLMResponseParser
from ..utils.config import config
from .prompts import (
    get_track_energy_analysis_system_prompt,
    get_track_energy_analysis_user_prompt,
    get_ordering_strategy_system_prompt,
    get_ordering_strategy_user_prompt,
)

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
                f"Playlist ordering complete",
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
            batch_tasks = [
                self._analyze_track_batch(batch, state.mood_prompt)
                for batch in batches
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Combine results from all batches
            all_analyses = []
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing batch {i+1}: {result}")
                    # Use fallback for failed batch
                    all_analyses.extend(self._fallback_energy_analysis(batches[i]))
                else:
                    all_analyses.extend(result)

            logger.info(f"Successfully analyzed {len(all_analyses)} tracks across {len(batches)} batches")
            return all_analyses

        except Exception as e:
            logger.error(f"Error in batch analysis: {e}", exc_info=True)
            return self._fallback_energy_analysis(state.recommendations)

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
        tracks_info = []
        for rec in tracks:
            track_info = {
                "track_id": rec.track_id,
                "track_name": f"{rec.track_name} - {rec.artists[0] if rec.artists else 'Unknown'}",
                "audio_features": rec.audio_features or {}
            }
            tracks_info.append(track_info)

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
            return self._get_default_strategy(avg_energy, energy_range, len(track_analyses))

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
        phase_buckets = self._assign_tracks_to_phases(
            recommendations,
            analysis_map,
            strategy
        )

        # Order tracks within each phase
        ordered_recommendations = []
        phase_order = ["opening", "build", "mid", "high", "descent", "closure"]

        for phase in phase_order:
            phase_tracks = phase_buckets.get(phase, [])
            if phase_tracks:
                # Sort within phase for smooth transitions
                sorted_phase = self._sort_tracks_within_phase(phase_tracks, analysis_map, phase)
                ordered_recommendations.extend(sorted_phase)
                logger.info(f"Phase '{phase}': {len(sorted_phase)} tracks")

        return ordered_recommendations

    def _assign_tracks_to_phases(
        self,
        recommendations: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]],
        strategy: Dict[str, Any]
    ) -> Dict[str, List[TrackRecommendation]]:
        """Assign tracks to energy flow phases.

        Args:
            recommendations: List of recommendations
            analysis_map: Mapping of track_id to analysis
            strategy: Ordering strategy

        Returns:
            Dictionary mapping phase names to track lists
        """
        phase_distribution = strategy.get("phase_distribution", {
            "opening": 2,
            "build": 5,
            "mid": 8,
            "high": 7,
            "descent": 4,
            "closure": 2
        })

        # Adjust distribution based on actual track count
        total_target = sum(phase_distribution.values())
        actual_count = len(recommendations)
        scale_factor = actual_count / total_target if total_target > 0 else 1

        adjusted_distribution = {
            phase: max(1, round(count * scale_factor))
            for phase, count in phase_distribution.items()
        }

        # Ensure we use all tracks
        diff = actual_count - sum(adjusted_distribution.values())
        if diff != 0:
            # Adjust the largest phase
            largest_phase = max(adjusted_distribution, key=adjusted_distribution.get)
            adjusted_distribution[largest_phase] += diff

        # Score each track for each phase
        track_phase_scores = []
        for rec in recommendations:
            analysis = analysis_map.get(rec.track_id, {})
            scores = self._calculate_phase_scores(rec, analysis)
            track_phase_scores.append((rec, analysis, scores))

        # Assign tracks to phases using greedy best-fit approach
        phase_buckets = {phase: [] for phase in adjusted_distribution.keys()}
        used_tracks = set()

        # First pass: assign tracks with strong phase preferences
        # Only iterate over phases that exist in the distribution
        phase_priority_order = ["opening", "closure", "high", "build", "descent", "mid"]
        for phase in phase_priority_order:
            if phase not in adjusted_distribution:
                continue
            target_count = adjusted_distribution[phase]
            
            # Get available tracks sorted by score for this phase
            available = [
                (rec, analysis, scores)
                for rec, analysis, scores in track_phase_scores
                if rec.track_id not in used_tracks
            ]
            available.sort(key=lambda x: x[2].get(phase, 0), reverse=True)

            # Assign top tracks to this phase
            for rec, analysis, scores in available[:target_count]:
                phase_buckets[phase].append(rec)
                used_tracks.add(rec.track_id)

                if len(phase_buckets[phase]) >= target_count:
                    break

        return phase_buckets

    def _calculate_phase_scores(
        self,
        recommendation: TrackRecommendation,
        analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate suitability scores for each phase.

        Args:
            recommendation: Track recommendation
            analysis: Track energy analysis

        Returns:
            Dictionary mapping phase names to scores
        """
        energy = analysis.get("energy_level", 50)
        momentum = analysis.get("momentum", 50)
        emotional_intensity = analysis.get("emotional_intensity", 50)
        opening_potential = analysis.get("opening_potential", 50)
        closing_potential = analysis.get("closing_potential", 50)
        peak_potential = analysis.get("peak_potential", 50)

        # Phase assignment from LLM (if available)
        llm_phase = analysis.get("phase_assignment")

        scores = {
            "opening": opening_potential * 1.5 if not llm_phase or llm_phase == "opening" else opening_potential * 0.5,
            "build": momentum * 0.8 + energy * 0.5 if energy < 70 else momentum * 0.3,
            "mid": (100 - abs(energy - 60)) * 0.7 + momentum * 0.5,
            "high": peak_potential * 1.5 + energy * 0.5 if energy > 60 else peak_potential * 0.5,
            "descent": (100 - momentum) * 0.7 + emotional_intensity * 0.5 if energy < 70 else (100 - momentum) * 0.3,
            "closure": closing_potential * 1.5 if not llm_phase or llm_phase == "closure" else closing_potential * 0.5,
        }

        # Boost score for LLM-assigned phase
        if llm_phase and llm_phase in scores:
            scores[llm_phase] *= 1.5

        return scores

    def _sort_tracks_within_phase(
        self,
        tracks: List[TrackRecommendation],
        analysis_map: Dict[str, Dict[str, Any]],
        phase: str
    ) -> List[TrackRecommendation]:
        """Sort tracks within a phase for smooth transitions.

        Args:
            tracks: Tracks in the phase
            analysis_map: Track analyses
            phase: Phase name

        Returns:
            Sorted tracks
        """
        if len(tracks) <= 1:
            return tracks

        # Define sorting criteria based on phase
        if phase == "opening":
            # Start with most welcoming, gradually build
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("opening_potential", 50),
                reverse=True
            )
        elif phase == "build":
            # Gradually increase energy
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("energy_level", 50)
            )
        elif phase == "high":
            # Keep peak energy, vary to maintain interest
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("peak_potential", 50),
                reverse=True
            )
        elif phase == "descent":
            # Gradually decrease energy
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("energy_level", 50),
                reverse=True
            )
        elif phase == "closure":
            # End with most satisfying resolution
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("closing_potential", 50),
                reverse=True
            )
        else:  # mid
            # Maintain consistent energy, vary by emotional intensity
            return sorted(
                tracks,
                key=lambda t: analysis_map.get(t.track_id, {}).get("emotional_intensity", 50),
                reverse=True
            )

    def _fallback_energy_analysis(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[Dict[str, Any]]:
        """Provide fallback energy analysis based on audio features.

        Args:
            recommendations: Track recommendations

        Returns:
            Basic energy analyses
        """
        logger.info("Using fallback energy analysis based on audio features")

        analyses = []
        for rec in recommendations:
            features = rec.audio_features or {}

            # Extract Spotify audio features
            energy = features.get("energy", 0.5) * 100
            tempo = features.get("tempo", 120)
            valence = features.get("valence", 0.5) * 100
            danceability = features.get("danceability", 0.5) * 100
            loudness = features.get("loudness", -10)

            # Calculate derived metrics
            energy_level = energy
            momentum = (tempo / 200 * 100 + danceability) / 2
            emotional_intensity = (abs(valence - 50) * 2 + energy) / 2

            # Heuristic potentials
            opening_potential = 60 if 40 < energy_level < 70 else 40
            closing_potential = 70 if energy_level < 50 or valence > 60 else 40
            peak_potential = energy_level if energy_level > 70 else 40

            # Assign phase based on energy level
            if energy_level < 40:
                phase = "opening" if opening_potential > 50 else "closure"
            elif energy_level < 60:
                phase = "build"
            elif energy_level < 75:
                phase = "mid"
            else:
                phase = "high"

            analyses.append({
                "track_id": rec.track_id,
                "track_name": f"{rec.track_name} - {rec.artists[0] if rec.artists else 'Unknown'}",
                "energy_level": energy_level,
                "momentum": momentum,
                "emotional_intensity": emotional_intensity,
                "opening_potential": opening_potential,
                "closing_potential": closing_potential,
                "peak_potential": peak_potential,
                "phase_assignment": phase,
                "reasoning": "Fallback analysis based on audio features"
            })

        return analyses

    def _get_default_strategy(
        self,
        avg_energy: float,
        energy_range: float,
        track_count: int
    ) -> Dict[str, Any]:
        """Get default ordering strategy based on track characteristics.

        Args:
            avg_energy: Average energy level
            energy_range: Range of energy levels
            track_count: Number of tracks

        Returns:
            Default strategy
        """
        # Determine strategy based on energy profile
        if avg_energy > 75:
            strategy_name = "sustained_energy"
        elif avg_energy < 35:
            strategy_name = "ambient_flow"
        elif energy_range > 50:
            strategy_name = "emotional_rollercoaster"
        else:
            strategy_name = "classic_build"

        # Calculate phase distribution
        if strategy_name == "sustained_energy":
            phase_dist = {
                "opening": max(1, track_count // 15),
                "build": max(2, track_count // 8),
                "mid": max(3, track_count // 4),
                "high": max(4, track_count // 3),
                "descent": max(2, track_count // 8),
                "closure": max(1, track_count // 15)
            }
        elif strategy_name == "ambient_flow":
            phase_dist = {
                "opening": max(2, track_count // 6),
                "build": max(3, track_count // 5),
                "mid": max(5, track_count // 3),
                "high": max(2, track_count // 8),
                "descent": max(3, track_count // 5),
                "closure": max(2, track_count // 6)
            }
        else:  # classic_build or emotional_rollercoaster
            phase_dist = {
                "opening": max(1, track_count // 10),
                "build": max(3, track_count // 6),
                "mid": max(4, track_count // 5),
                "high": max(3, track_count // 6),
                "descent": max(2, track_count // 8),
                "closure": max(1, track_count // 10)
            }

        return {
            "strategy": strategy_name,
            "reasoning": f"Default strategy based on avg_energy={avg_energy:.1f}, range={energy_range:.1f}",
            "phase_distribution": phase_dist,
            "special_considerations": [],
            "transition_notes": "Smooth transitions based on audio feature similarity"
        }

