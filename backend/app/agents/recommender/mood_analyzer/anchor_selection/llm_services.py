"""LLM services for anchor track selection."""

import re
import structlog
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models.base import BaseLanguageModel

from ...utils.llm_response_parser import LLMResponseParser
from .prompts import (
    get_track_extraction_prompt,
    get_anchor_strategy_prompt,
    get_anchor_scoring_prompt,
    get_anchor_finalization_prompt,
    get_batch_track_filter_prompt,
    get_batch_artist_validation_prompt,
)
from .types import AnchorCandidate, AnchorSelectionStrategy

logger = structlog.get_logger(__name__)


class LLMServices:
    """Handles all LLM operations for anchor track selection."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """Initialize LLM services.

        Args:
            llm: Language model for processing
        """
        self.llm = llm

    async def extract_user_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str]
    ) -> List[Tuple[str, str]]:
        """Extract specific tracks mentioned by the user using LLM.

        Args:
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis

        Returns:
            List of (track_name, artist_name) tuples
        """
        if not self.llm or not mood_prompt:
            return []

        try:
            prompt = get_track_extraction_prompt(mood_prompt, artist_recommendations)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

            # Parse using centralized parser utility
            result = LLMResponseParser.extract_json_from_response(response)

            mentioned_tracks = result.get("mentioned_tracks", [])
            reasoning = result.get("reasoning", "")

            if mentioned_tracks:
                logger.info(f"LLM extracted {len(mentioned_tracks)} mentioned tracks: {reasoning}")
                return [(t.get("track_name", ""), t.get("artist_name", "")) for t in mentioned_tracks]
            else:
                logger.info("LLM found no specific tracks mentioned in prompt")
                return []

        except Exception as e:
            logger.error(f"LLM track extraction failed: {e}")
            return []

    def simple_extract_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str]
    ) -> List[Tuple[str, str]]:
        """Simple fallback pattern matching for track extraction.

        Args:
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis

        Returns:
            List of (track_name, artist_name) tuples
        """
        track_hints: List[Tuple[str, str]] = []
        primary_artist = artist_recommendations[0] if artist_recommendations else ""
        seen: set[Tuple[str, str]] = set()

        def _add_hint(track: str, artist: str) -> None:
            track_clean = track.strip().strip('\'"')
            artist_clean = artist.strip().strip('\'"')
            if not track_clean or len(track_clean) < 2:
                return
            key = (track_clean.lower(), artist_clean.lower())
            if key in seen:
                return
            seen.add(key)
            track_hints.append((track_clean, artist_clean))
            logger.info(f"Extracted track reference: '{track_clean}' by '{artist_clean}'")

        # Normalize whitespace for consistent matching
        normalized_prompt = "\n".join(line.strip() for line in mood_prompt.splitlines() if line.strip())

        # Pattern 1: "things like/stuff like/songs like <track> by <artist>"
        pattern_like_by = re.compile(
            r"(?:things|stuff|songs)\s+like\s+\"?([^\n\"']+?)\"?\s+by\s+([^\n,;:.!?]+)",
            re.IGNORECASE
        )
        for match in pattern_like_by.finditer(normalized_prompt):
            track_name = match.group(1)
            artist_name = match.group(2)
            _add_hint(track_name, artist_name)

        # Pattern 2: General "[track] by [artist]" on standalone lines
        pattern_track_by = re.compile(r"^['\"]?([^\n\"']+?)['\"]?\s+by\s+([^\n,;:.!?]+)$", re.IGNORECASE)
        for line in normalized_prompt.split("\n"):
            match = pattern_track_by.search(line)
            if match:
                track_name = match.group(1)
                artist_name = match.group(2)
                _add_hint(track_name, artist_name)

        # Pattern 3: "especially [track]" (assume primary artist)
        pattern_especially = re.compile(r"especially\s+['\"]?([^\n,;:.!?]+)", re.IGNORECASE)
        for match in pattern_especially.finditer(normalized_prompt):
            track_name = match.group(1)
            _add_hint(track_name, primary_artist)

        # Pattern 4: "like [track]" (without explicit artist)
        pattern_plain_like = re.compile(r"like\s+['\"]?([^\n,;:.!?]+)", re.IGNORECASE)
        for match in pattern_plain_like.finditer(normalized_prompt):
            track_segment = match.group(1)
            if " by " in track_segment.lower():
                track_part, artist_part = track_segment.split(" by ", 1)
                _add_hint(track_part, artist_part)
            else:
                _add_hint(track_segment, primary_artist)

        return track_hints

    async def get_anchor_selection_strategy(
        self,
        mood_prompt: str,
        mood_analysis: Dict[str, Any],
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> AnchorSelectionStrategy:
        """Use LLM to determine the optimal strategy for anchor track selection.

        Args:
            mood_prompt: User's mood prompt
            mood_analysis: Full mood analysis
            genre_keywords: Genre keywords
            target_features: Target audio features
            candidates: Available track candidates

        Returns:
            Strategy configuration
        """
        if not self.llm:
            return AnchorSelectionStrategy(
                anchor_count=5,
                selection_criteria={
                    "prioritize_user_mentioned": True,
                    "feature_weights": {
                        "danceability": 1.0,
                        "energy": 0.9,
                        "valence": 0.8,
                        "tempo": 0.9,
                        "instrumentalness": 0.7
                    },
                    "popularity_weight": 0.3,
                    "genre_diversity": True
                }
            )

        try:
            prompt = get_anchor_strategy_prompt(
                mood_prompt, mood_analysis, genre_keywords, target_features, candidates
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            logger.info("LLM determined anchor selection strategy")
            return AnchorSelectionStrategy(
                anchor_count=result.get('anchor_count', 5),
                selection_criteria=result.get('selection_criteria', {}),
                track_priorities=result.get('track_priorities'),
                strategy_notes=result.get('strategy_notes')
            )

        except Exception as e:
            logger.warning(f"Failed to get LLM anchor strategy: {e}")
            # Return default strategy
            return AnchorSelectionStrategy(
                anchor_count=5,
                selection_criteria={
                    "prioritize_user_mentioned": True,
                    "feature_weights": {
                        "danceability": 1.0,
                        "energy": 0.9,
                        "valence": 0.8,
                        "tempo": 0.9,
                        "instrumentalness": 0.7
                    },
                    "popularity_weight": 0.3,
                    "genre_diversity": True
                }
            )

    async def score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        target_features: Dict[str, Any],
        mood_analysis: Dict[str, Any],
        selection_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to score anchor track candidates.

        Args:
            candidates: List of track candidates
            target_features: Target audio features
            mood_analysis: Mood analysis context
            selection_criteria: Criteria from strategy analysis

        Returns:
            List of candidates with LLM-assigned scores
        """
        if not self.llm:
            # Return candidates with default scores
            for candidate in candidates:
                candidate['llm_score'] = 0.6
                candidate['llm_confidence'] = 0.5
                candidate['llm_reasoning'] = 'Default scoring due to no LLM'
            return candidates

        try:
            prompt = get_anchor_scoring_prompt(
                candidates, target_features, selection_criteria
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            track_scores = result.get('track_scores', [])

            # Attach scores back to candidates
            scored_candidates = []
            for score_data in track_scores:
                track_index = score_data.get('track_index', 0)
                if 0 <= track_index < len(candidates):
                    candidate = candidates[track_index].copy()
                    candidate['llm_score'] = score_data.get('score', 0.5)
                    candidate['llm_confidence'] = score_data.get('confidence', 0.5)
                    candidate['llm_reasoning'] = score_data.get('reasoning', '')
                    scored_candidates.append(candidate)

            logger.info(f"LLM scored {len(scored_candidates)} anchor candidates")
            return scored_candidates

        except Exception as e:
            logger.warning(f"Failed to get LLM candidate scores: {e}")
            # Return candidates with default scores
            for candidate in candidates:
                candidate['llm_score'] = 0.6
                candidate['llm_confidence'] = 0.5
                candidate['llm_reasoning'] = 'Default scoring due to LLM failure'
            return candidates

    async def finalize_selection(
        self,
        scored_candidates: List[Dict[str, Any]],
        target_count: int,
        mood_analysis: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Use LLM to finalize the selection of anchor tracks.

        Args:
            scored_candidates: Candidates with LLM scores
            target_count: Target number of anchors
            mood_analysis: Mood analysis context

        Returns:
            Tuple of (selected_tracks, selected_track_ids)
        """
        if not self.llm:
            # Fallback: sort by score and take top N
            scored_candidates.sort(key=lambda x: x.get('llm_score', 0), reverse=True)
            top_candidates = scored_candidates[:target_count]

            selected_tracks = [c.get('track', {}) for c in top_candidates]
            selected_ids = [t.get('id') for t in selected_tracks if t.get('id')]

            return selected_tracks, selected_ids

        try:
            prompt = get_anchor_finalization_prompt(
                scored_candidates, target_count, mood_analysis
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            selected_indices = result.get('selected_indices', [])
            selection_reasoning = result.get('selection_reasoning', '')

            # Extract selected tracks and IDs
            selected_tracks = []
            selected_ids = []

            for idx in selected_indices:
                if 0 <= idx < len(scored_candidates):
                    candidate = scored_candidates[idx]
                    track = candidate.get('track', {})

                    # Add LLM metadata
                    track['llm_score'] = candidate.get('llm_score', 0.5)
                    track['llm_reasoning'] = candidate.get('llm_reasoning', '')
                    track['anchor_type'] = candidate.get('anchor_type', 'llm_selected')
                    track['protected'] = candidate.get('protected', False)

                    selected_tracks.append(track)
                    if track.get('id'):
                        selected_ids.append(track['id'])

            logger.info(
                f"LLM finalized selection of {len(selected_tracks)} anchor tracks: {selection_reasoning}"
            )

            return selected_tracks, selected_ids

        except Exception as e:
            logger.warning(f"Failed to finalize LLM selection: {e}")
            # Fallback: sort by LLM score and take top N
            scored_candidates.sort(key=lambda x: x.get('llm_score', 0), reverse=True)
            top_candidates = scored_candidates[:target_count]

            selected_tracks = [c.get('track', {}) for c in top_candidates]
            selected_ids = [t.get('id') for t in selected_tracks if t.get('id')]

            return selected_tracks, selected_ids

    async def batch_validate_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to batch validate artists for cultural/genre relevance.

        Args:
            artists: List of artist information from Spotify
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis context

        Returns:
            List of validated artists
        """
        if not self.llm or not artists:
            return artists  # No LLM available, allow all by default

        try:
            prompt = get_batch_artist_validation_prompt(artists, mood_prompt, mood_analysis)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            keep_indices = result.get('keep_artists', [])
            filtered_info = result.get('filtered_artists', [])

            # Log filtered artists
            for filter_info in filtered_info:
                name = filter_info.get('name', 'Unknown')
                reason = filter_info.get('reason', '')
                logger.info(f"LLM filtered artist '{name}': {reason}")

            # Return validated artists
            validated = []
            for idx in keep_indices:
                if 0 <= idx < len(artists):
                    validated.append(artists[idx])

            logger.info(f"Batch artist validation: kept {len(validated)}/{len(artists)} artists")
            return validated

        except Exception as e:
            logger.warning(f"Batch artist validation LLM call failed: {e}")
            return artists  # Default to allowing all if LLM fails

    async def filter_tracks_by_relevance(
        self,
        tracks: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to filter out culturally/linguistically irrelevant tracks.

        Args:
            tracks: List of track candidates
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis context

        Returns:
            Filtered list of relevant tracks
        """
        if not self.llm or not tracks:
            return tracks

        try:
            # Format tracks for LLM
            tracks_for_llm = []
            for track in tracks:
                track_data = track.get('track', track)
                tracks_for_llm.append({
                    'name': track_data.get('name', ''),
                    'artists': track_data.get('artists', [])
                })

            prompt = get_batch_track_filter_prompt(tracks_for_llm, mood_prompt, mood_analysis)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            relevant_indices = set(result.get('relevant_tracks', []))
            filtered_out = result.get('filtered_out', [])

            # Log filtered tracks
            for filter_info in filtered_out:
                track_idx = filter_info.get('track_index', -1)
                reason = filter_info.get('reason', '')
                if 0 <= track_idx < len(tracks_for_llm):
                    track_name = tracks_for_llm[track_idx].get('name', 'Unknown')
                    logger.info(f"LLM filtered track '{track_name}': {reason}")

            # Return only relevant tracks
            filtered_tracks = [
                tracks[i] for i in range(len(tracks))
                if i in relevant_indices
            ]

            logger.info(
                f"LLM track filtering: kept {len(filtered_tracks)}/{len(tracks)} tracks"
            )

            return filtered_tracks

        except Exception as e:
            logger.warning(f"Track filtering LLM call failed: {e}")
            return tracks  # Return all tracks if LLM fails