"""LLM services for anchor track selection."""

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
                track_list = [(t.get("track_name", ""), t.get("artist_name", "")) for t in mentioned_tracks]
                logger.info(
                    f"✓ LLM extracted {len(mentioned_tracks)} user-mentioned tracks: {reasoning}"
                )
                for track_name, artist_name in track_list:
                    logger.info(f"  - '{track_name}' by {artist_name}")
                return track_list
            else:
                logger.info("LLM found no specific tracks mentioned in prompt")
                return []

        except Exception as e:
            logger.error(f"LLM track extraction failed: {e}", exc_info=True)
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
        track_hints = []

        # Look for "especially" followed by track names
        if "especially" in mood_prompt.lower():
            parts = mood_prompt.split("especially")
            if len(parts) > 1:
                after_especially = parts[1].strip()
                # Split by "and" or ","
                if "," in after_especially:
                    tracks = after_especially.split(",")
                elif " and " in after_especially.lower():
                    tracks = after_especially.split(" and ")
                else:
                    tracks = [after_especially]

                # Clean up track names
                primary_artist = artist_recommendations[0] if artist_recommendations else ""
                for track in tracks[:3]:
                    track_name = track.split(".")[0].split("?")[0].strip().rstrip(",;:")
                    if track_name and len(track_name) > 2:
                        track_hints.append((track_name, primary_artist))

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
        
        User-mentioned tracks (anchor_type="user") are ALWAYS included.
        LLM only selects additional tracks to fill remaining slots.

        Args:
            scored_candidates: Candidates with LLM scores
            target_count: Target number of anchors
            mood_analysis: Mood analysis context

        Returns:
            Tuple of (selected_tracks, selected_track_ids)
        """
        # STEP 1: Extract user-mentioned tracks (GUARANTEED inclusion)
        user_mentioned = []
        other_candidates = []
        
        for candidate in scored_candidates:
            if candidate.get('anchor_type') == 'user' or candidate.get('user_mentioned'):
                user_mentioned.append(candidate)
            else:
                other_candidates.append(candidate)
        
        # Preserve user-mentioned metadata
        selected_tracks = []
        selected_ids = []
        
        for candidate in user_mentioned:
            track = candidate.get('track', {})
            # CRITICAL: Preserve user-mentioned metadata
            track['user_mentioned'] = True
            track['anchor_type'] = 'user'
            track['protected'] = True
            track['confidence'] = candidate.get('confidence', 1.0)
            track['llm_score'] = candidate.get('llm_score', 1.0)
            track['llm_reasoning'] = candidate.get('llm_reasoning', 'User explicitly mentioned this track')
            
            selected_tracks.append(track)
            if track.get('id'):
                selected_ids.append(track['id'])
        
        logger.info(
            f"✓ Guaranteed inclusion of {len(user_mentioned)} user-mentioned tracks"
        )
        
        # STEP 2: Fill remaining slots with LLM selection
        remaining_slots = max(0, target_count - len(user_mentioned))
        
        if remaining_slots == 0:
            logger.info(f"Target count ({target_count}) reached with user-mentioned tracks only")
            return selected_tracks, selected_ids
        
        if not other_candidates:
            logger.info(f"No additional candidates to fill remaining {remaining_slots} slots")
            return selected_tracks, selected_ids
        
        # CRITICAL: Filter out low-quality anchors (llm_score < 0.6)
        # Only user-mentioned tracks are protected - genre anchors must meet quality threshold
        quality_threshold = 0.6
        quality_candidates = [
            c for c in other_candidates 
            if c.get('llm_score', 0) >= quality_threshold
        ]
        
        filtered_count = len(other_candidates) - len(quality_candidates)
        if filtered_count > 0:
            logger.info(
                f"✓ Filtered {filtered_count} low-quality anchors (llm_score < {quality_threshold})"
            )
            # Log which tracks were filtered
            for candidate in other_candidates:
                if candidate.get('llm_score', 0) < quality_threshold:
                    track = candidate.get('track', {})
                    logger.info(
                        f"  ✗ Rejected: '{track.get('name')}' by {[a.get('name') for a in track.get('artists', [])]} "
                        f"(llm_score={candidate.get('llm_score', 0):.2f})"
                    )
        
        # Use quality candidates for selection
        other_candidates = quality_candidates
        
        if not other_candidates:
            logger.warning(f"No quality candidates remain after filtering (threshold={quality_threshold})")
            return selected_tracks, selected_ids
        
        # Use LLM or fallback to select additional tracks
        if not self.llm:
            # Fallback: sort by score and take top N
            other_candidates.sort(key=lambda x: x.get('llm_score', 0), reverse=True)
            additional = other_candidates[:remaining_slots]
            
            for candidate in additional:
                track = candidate.get('track', {})
                track['llm_score'] = candidate.get('llm_score', 0.5)
                track['llm_reasoning'] = candidate.get('llm_reasoning', '')
                track['anchor_type'] = candidate.get('anchor_type', 'genre')
                track['protected'] = candidate.get('protected', False)
                track['user_mentioned'] = False
                
                selected_tracks.append(track)
                if track.get('id'):
                    selected_ids.append(track['id'])
            
            logger.info(f"Added {len(additional)} additional tracks (no LLM, score-based)")
            return selected_tracks, selected_ids

        try:
            prompt = get_anchor_finalization_prompt(
                other_candidates, remaining_slots, mood_analysis
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            selected_indices = result.get('selected_indices', [])
            selection_reasoning = result.get('selection_reasoning', '')

            # Extract selected tracks and IDs
            for idx in selected_indices[:remaining_slots]:
                if 0 <= idx < len(other_candidates):
                    candidate = other_candidates[idx]
                    track = candidate.get('track', {})

                    # Add LLM metadata
                    track['llm_score'] = candidate.get('llm_score', 0.5)
                    track['llm_reasoning'] = candidate.get('llm_reasoning', '')
                    track['anchor_type'] = candidate.get('anchor_type', 'llm_selected')
                    track['protected'] = candidate.get('protected', False)
                    track['user_mentioned'] = False

                    selected_tracks.append(track)
                    if track.get('id'):
                        selected_ids.append(track['id'])

            logger.info(
                f"✓ LLM selected {len(selected_indices)} additional anchor tracks: {selection_reasoning}"
            )
            logger.info(
                f"Final anchor selection: {len(user_mentioned)} user-mentioned + "
                f"{len(selected_tracks) - len(user_mentioned)} LLM-selected = {len(selected_tracks)} total"
            )

            return selected_tracks, selected_ids

        except Exception as e:
            logger.warning(f"Failed to finalize LLM selection: {e}")
            # Fallback: sort by LLM score and take top N
            other_candidates.sort(key=lambda x: x.get('llm_score', 0), reverse=True)
            additional = other_candidates[:remaining_slots]

            for candidate in additional:
                track = candidate.get('track', {})
                track['llm_score'] = candidate.get('llm_score', 0.5)
                track['llm_reasoning'] = candidate.get('llm_reasoning', '')
                track['anchor_type'] = candidate.get('anchor_type', 'genre')
                track['protected'] = candidate.get('protected', False)
                track['user_mentioned'] = False
                
                selected_tracks.append(track)
                if track.get('id'):
                    selected_ids.append(track['id'])

            logger.info(f"Added {len(additional)} additional tracks (LLM failed, score-based fallback)")
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

            # Log filtered tracks (but protect user-mentioned tracks)
            protected_count = 0
            for filter_info in filtered_out:
                track_idx = filter_info.get('track_index', -1)
                reason = filter_info.get('reason', '')
                if 0 <= track_idx < len(tracks_for_llm):
                    track_name = tracks_for_llm[track_idx].get('name', 'Unknown')
                    
                    # Check if this track is user-mentioned/protected
                    track_data = tracks[track_idx].get('track', tracks[track_idx])
                    is_protected = track_data.get('user_mentioned', False) or track_data.get('protected', False)
                    
                    if is_protected:
                        protected_count += 1
                        logger.info(
                            f"✓ PROTECTED: LLM tried to filter '{track_name}' but it's user-mentioned (reason: {reason})"
                        )
                        # Force include protected tracks
                        relevant_indices.add(track_idx)
                    else:
                        logger.info(f"LLM filtered track '{track_name}': {reason}")

            # Return only relevant tracks (plus protected tracks)
            filtered_tracks = [
                tracks[i] for i in range(len(tracks))
                if i in relevant_indices
            ]

            logger.info(
                f"LLM track filtering: kept {len(filtered_tracks)}/{len(tracks)} tracks "
                f"({protected_count} protected from filtering)"
            )

            return filtered_tracks

        except Exception as e:
            logger.warning(f"Track filtering LLM call failed: {e}")
            return tracks  # Return all tracks if LLM fails