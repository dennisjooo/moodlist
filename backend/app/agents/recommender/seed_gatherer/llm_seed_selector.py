"""LLM-based seed selector for intelligent seed selection."""

from typing import Any, Dict, List

import structlog

from ..utils.llm_response_parser import LLMResponseParser
from .prompts.seed_selection import get_seed_selection_prompt

logger = structlog.get_logger(__name__)


class LLMSeedSelector:
    """Handles LLM-based seed selection from candidate tracks."""

    def __init__(self, llm=None):
        """Initialize the LLM seed selector.

        Args:
            llm: Language model for intelligent seed selection
        """
        self.llm = llm

    async def select_seeds(
        self,
        candidate_track_ids: List[str],
        mood_prompt: str,
        target_features: Dict[str, Any],
        ideal_count: int = 8,
    ) -> List[str]:
        """Use LLM to select the best seed tracks from candidates.

        Args:
            candidate_track_ids: List of candidate track IDs (already scored)
            mood_prompt: User's mood description
            target_features: Target audio features
            ideal_count: Ideal number of seeds to select

        Returns:
            List of selected seed track IDs
        """
        if not self.llm:
            logger.warning("No LLM available for seed selection")
            return candidate_track_ids[:ideal_count]

        try:
            # We need track details for the LLM prompt
            # For now, use the track IDs directly and trust the scoring
            # In a more complete implementation, we'd fetch track metadata

            logger.info(
                f"LLM selecting seeds from {len(candidate_track_ids)} candidates for mood: '{mood_prompt}'"
            )

            # Create a summary of target features for LLM
            features_summary = []
            for feature, value in list(target_features.items())[:5]:
                if feature != "_weights":
                    if isinstance(value, list):
                        features_summary.append(
                            f"{feature}: {value[0]:.2f}-{value[1]:.2f}"
                        )
                    else:
                        features_summary.append(f"{feature}: {value:.2f}")

            prompt = get_seed_selection_prompt(
                mood_prompt=mood_prompt,
                features_summary=features_summary,
                candidate_count=len(candidate_track_ids),
                ideal_count=ideal_count,
                candidate_tracks=candidate_track_ids,
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            # Parse JSON response using centralized parser
            result = LLMResponseParser.extract_json_from_response(response)

            if result:
                selected_indices = result.get("selected_indices", [])
                reasoning = result.get("reasoning", "")

                # Map indices to track IDs (1-indexed in prompt, 0-indexed in list)
                selected_tracks = [
                    candidate_track_ids[idx - 1]
                    for idx in selected_indices
                    if 1 <= idx <= len(candidate_track_ids)
                ]

                # Store reasoning in metadata
                logger.info(f"LLM selected {len(selected_tracks)} seeds: {reasoning}")

                # Return up to ideal_count seeds
                return selected_tracks[:ideal_count]

            else:
                logger.warning("Could not parse LLM seed selection response")
                return candidate_track_ids[:ideal_count]

        except Exception as e:
            logger.error(f"LLM seed selection failed: {str(e)}")
            # Fallback to top scored tracks
            return candidate_track_ids[:ideal_count]
