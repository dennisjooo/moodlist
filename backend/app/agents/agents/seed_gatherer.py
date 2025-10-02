"""Seed gatherer agent for collecting user preference data."""

import logging
from typing import Any, Dict, List, Optional

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ..tools.spotify_service import SpotifyService


logger = logging.getLogger(__name__)


class SeedGathererAgent(BaseAgent):
    """Agent for gathering seed tracks and artists from user data."""

    def __init__(
        self,
        spotify_service: SpotifyService,
        reccobeat_service=None,
        llm=None,
        verbose: bool = False
    ):
        """Initialize the seed gatherer agent.

        Args:
            spotify_service: Service for Spotify API operations
            reccobeat_service: Service for RecoBeat API operations (for audio features)
            llm: Language model for intelligent seed selection
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="seed_gatherer",
            description="Gathers seed tracks and artists from user's Spotify listening history",
            llm=llm,
            verbose=verbose
        )

        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

    async def execute(self, state: AgentState) -> AgentState:
        """Execute seed gathering from user's Spotify data.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with seed data
        """
        try:
            logger.info(f"Gathering seeds for user {state.user_id}")

            # Check if we have Spotify access token
            if not hasattr(state, 'access_token') or not state.access_token:
                # Try to get from metadata or user record
                access_token = state.metadata.get("spotify_access_token")
                if not access_token:
                    raise ValueError("No Spotify access token available for seed gathering")

            # Get user's top tracks for seeds
            top_tracks = await self.spotify_service.get_user_top_tracks(
                access_token=access_token,
                limit=20,
                time_range="medium_term"
            )

            # Get user's top artists for additional context
            top_artists = await self.spotify_service.get_user_top_artists(
                access_token=access_token,
                limit=15,
                time_range="medium_term"
            )

            # Process and select seed tracks
            # Get target features and weights from metadata where mood analyzer stored them
            target_features = state.metadata.get("target_features", {})
            feature_weights = state.metadata.get("feature_weights", {})

            # Enhance target_features with weights for more sophisticated matching
            if feature_weights:
                target_features["_weights"] = feature_weights

            # Fetch audio features for top tracks if RecoBeat service available
            if self.reccobeat_service:
                top_tracks = await self._enrich_tracks_with_features(top_tracks)

            # Select seed tracks using audio feature scoring
            scored_tracks = self._select_seed_tracks(top_tracks, target_features)
            
            # Use LLM to select final seeds if available
            if self.llm and len(scored_tracks) > 5:
                final_seeds = await self._llm_select_seeds(
                    scored_tracks[:15],  # Top 15 candidates
                    state.mood_prompt,
                    target_features
                )
            else:
                # Just use top scored tracks
                final_seeds = scored_tracks[:10]
            
            state.seed_tracks = final_seeds
            state.metadata["seed_candidates_count"] = len(scored_tracks)

            # Extract artist IDs for context
            artist_ids = [artist["id"] for artist in top_artists if artist.get("id")]
            state.user_top_artists = artist_ids

            # Update state
            state.current_step = "seeds_gathered"
            state.status = RecommendationStatus.GATHERING_SEEDS

            # Store additional metadata
            state.metadata["seed_track_count"] = len(final_seeds)
            state.metadata["top_artist_count"] = len(artist_ids)
            state.metadata["seed_source"] = "spotify_top_tracks_ai_selected"

            logger.info(f"Gathered {len(final_seeds)} seed tracks and {len(artist_ids)} artists")

        except Exception as e:
            logger.error(f"Error in seed gathering: {str(e)}", exc_info=True)
            state.set_error(f"Seed gathering failed: {str(e)}")

        return state

    def _select_seed_tracks(
        self,
        top_tracks: List[Dict[str, Any]],
        target_features: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Select the best tracks to use as seeds with scoring.

        Args:
            top_tracks: User's top tracks from Spotify
            target_features: Target audio features from mood analysis

        Returns:
            List of selected track IDs (ordered by score)
        """
        if not top_tracks:
            logger.warning("No top tracks available for seed selection")
            return []

        # Filter out tracks without IDs
        valid_tracks = [track for track in top_tracks if track.get("id")]

        if not valid_tracks:
            logger.warning("No valid track IDs found in top tracks")
            return []

        # Prioritize tracks that match mood if target features available
        if target_features:
            # Score tracks based on how well they match the target features
            scored_tracks = []
            for track in valid_tracks[:30]:  # Consider top 30 tracks
                score = self._calculate_mood_match_score(track, target_features)
                scored_tracks.append((track["id"], score, track))

            # Sort by score and return track IDs
            scored_tracks.sort(key=lambda x: x[1], reverse=True)
            selected_tracks = [track_id for track_id, _, _ in scored_tracks]

            logger.info(f"Scored {len(scored_tracks)} tracks, top score: {scored_tracks[0][1]:.2f}")
            return selected_tracks

        else:
            # Default selection: take top tracks by popularity
            sorted_tracks = sorted(
                valid_tracks,
                key=lambda x: x.get("popularity", 0),
                reverse=True
            )
            selected_tracks = [track["id"] for track in sorted_tracks]

        logger.info(f"Selected {len(selected_tracks)} seed track candidates")
        return selected_tracks

    def _calculate_mood_match_score(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track matches target mood features using all available audio features and weights.

        Args:
            track: Track information from Spotify
            target_features: Target audio features from mood analysis (may include _weights)

        Returns:
            Match score (0-1, higher is better)
        """
        if not target_features:
            # Fallback to popularity if no target features
            return track.get("popularity", 50) / 100.0

        # Extract feature weights if provided, otherwise use defaults
        feature_weights = target_features.get("_weights", self._get_default_feature_weights())

        total_score = 0.0
        total_weight = 0.0

        # Calculate match score for each available feature
        for feature, target_value in target_features.items():
            if feature == "_weights" or feature not in feature_weights:
                continue

            weight = feature_weights.get(feature, 0.1)  # Default weight if not specified
            track_value = self._get_track_feature_value(track, feature)

            if track_value is not None:
                # Calculate similarity score (0-1) for this feature
                feature_score = self._calculate_feature_similarity(
                    track_value, target_value, feature
                )

                total_score += feature_score * weight
                total_weight += weight

        # Normalize by total weight
        if total_weight == 0:
            return track.get("popularity", 50) / 100.0

        final_score = total_score / total_weight

        # Boost score slightly for popular tracks (they're likely to be good seeds)
        popularity_boost = min(track.get("popularity", 50) / 1000.0, 0.1)

        return min(final_score + popularity_boost, 1.0)

    def _get_default_feature_weights(self) -> Dict[str, float]:
        """Get default feature weights when none are provided by mood analysis."""
        return {
            "energy": 0.15,
            "valence": 0.15,
            "danceability": 0.12,
            "acousticness": 0.12,
            "instrumentalness": 0.10,
            "tempo": 0.08,
            "mode": 0.08,
            "loudness": 0.06,
            "speechiness": 0.05,
            "liveness": 0.05,
            "key": 0.03,
            "popularity": 0.01
        }

    def _get_track_feature_value(self, track: Dict[str, Any], feature: str) -> Optional[float]:
        """Extract feature value from Spotify track data.

        Args:
            track: Spotify track information
            feature: Feature name to extract

        Returns:
            Feature value or None if not available
        """
        # Map feature names to Spotify track structure
        feature_mapping = {
            "energy": track.get("energy"),
            "valence": track.get("valence"),
            "danceability": track.get("danceability"),
            "acousticness": track.get("acousticness"),
            "instrumentalness": track.get("instrumentalness"),
            "tempo": track.get("tempo"),
            "mode": track.get("mode"),
            "loudness": track.get("loudness"),
            "speechiness": track.get("speechiness"),
            "liveness": track.get("liveness"),
            "key": track.get("key"),
            "popularity": track.get("popularity")
        }

        return feature_mapping.get(feature)

    def _calculate_feature_similarity(
        self,
        track_value: float,
        target_value: float,
        feature: str
    ) -> float:
        """Calculate similarity between track feature and target feature.

        Args:
            track_value: Actual feature value from track
            target_value: Target feature value from mood analysis
            feature: Name of the feature being compared

        Returns:
            Similarity score (0-1, higher is better)
        """
        if feature in ["tempo", "loudness", "key", "popularity"]:
            # For continuous numeric features, use distance-based similarity
            if feature == "tempo":
                # Tempo similarity - closer BPMs are more similar
                max_diff = 60  # BPM
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "loudness":
                # Loudness similarity - closer dB values are more similar
                max_diff = 30  # dB
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))
            elif feature == "key":
                # Key similarity - exact match or adjacent keys
                if track_value == target_value:
                    return 1.0
                elif abs(track_value - target_value) == 1:
                    return 0.8  # Adjacent keys are somewhat similar
                else:
                    return 0.3  # Other keys are less similar
            elif feature == "popularity":
                # Popularity similarity - lower popularity for indie moods
                max_diff = 100
                diff = abs(track_value - target_value)
                return max(0, 1 - (diff / max_diff))

        # For normalized features (0-1), use direct distance
        diff = abs(track_value - target_value)
        return max(0, 1 - diff)

    def _get_negative_seeds(
        self,
        top_tracks: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[str]:
        """Get tracks to avoid in recommendations.

        Args:
            top_tracks: User's top tracks
            mood_analysis: Optional mood analysis
            limit: Maximum number of negative seeds

        Returns:
            List of track IDs to avoid
        """
        # For now, we'll use least popular tracks as negative examples
        # This is a simple heuristic - could be enhanced

        valid_tracks = [track for track in top_tracks if track.get("id")]

        # Sort by popularity (ascending) - least popular first
        sorted_tracks = sorted(
            valid_tracks,
            key=lambda x: x.get("popularity", 50)
        )

        # Take least popular tracks as negative examples
        negative_seeds = [track["id"] for track in sorted_tracks[:limit]]

        logger.info(f"Selected {len(negative_seeds)} negative seed tracks")

        return negative_seeds

    async def _enrich_tracks_with_features(
        self,
        tracks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich tracks with audio features from RecoBeat.

        Args:
            tracks: List of track dictionaries

        Returns:
            Tracks enriched with audio features
        """
        if not self.reccobeat_service:
            return tracks

        logger.info(f"Fetching audio features for {len(tracks)} tracks")
        enriched_tracks = []
        for track in tracks:
            track_id = track.get("track_id") or track.get("id")
            if not track_id:
                enriched_tracks.append(track)
                continue

            try:
                # Fetch audio features from RecoBeat
                features_map = await self.reccobeat_service.get_tracks_audio_features([track_id])
                
                if track_id in features_map:
                    # Merge audio features into track data
                    track_with_features = track.copy()
                    track_with_features.update(features_map[track_id])
                    enriched_tracks.append(track_with_features)
                else:
                    enriched_tracks.append(track)

            except Exception as e:
                logger.warning(f"Failed to fetch features for track {track_id}: {e}")
                enriched_tracks.append(track)

        logger.info(f"Successfully enriched {len([t for t in enriched_tracks if 'energy' in t])} tracks with audio features")
        return enriched_tracks

    async def _llm_select_seeds(
        self,
        candidate_track_ids: List[str],
        mood_prompt: str,
        target_features: Dict[str, Any]
    ) -> List[str]:
        """Use LLM to select the best seed tracks from candidates.

        Args:
            candidate_track_ids: List of candidate track IDs (already scored)
            mood_prompt: User's mood description
            target_features: Target audio features

        Returns:
            List of 5-8 selected seed track IDs
        """
        try:
            # We need track details for the LLM prompt
            # For now, use the track IDs directly and trust the scoring
            # In a more complete implementation, we'd fetch track metadata
            
            logger.info(f"LLM selecting seeds from {len(candidate_track_ids)} candidates for mood: '{mood_prompt}'")

            # Create a summary of target features for LLM
            features_summary = []
            for feature, value in list(target_features.items())[:5]:
                if feature != "_weights":
                    if isinstance(value, list):
                        features_summary.append(f"{feature}: {value[0]:.2f}-{value[1]:.2f}")
                    else:
                        features_summary.append(f"{feature}: {value:.2f}")

            prompt = f"""You are a music curator selecting seed tracks for a mood-based playlist.

**User's Mood**: "{mood_prompt}"

**Target Audio Features**: {", ".join(features_summary)}

**Task**: From the provided {len(candidate_track_ids)} candidate tracks (already ranked by how well they match the mood), select 5-8 tracks that would make the best seeds for generating a cohesive playlist.

Consider:
1. The tracks are already scored and ordered by match quality
2. Select tracks that exemplify the mood
3. Prefer variety in the seeds (don't pick all similar tracks)
4. Balance between strong mood matches and diversity

**Candidates** (ranked by score):
{chr(10).join([f"{i+1}. Track {track_id[:8]}..." for i, track_id in enumerate(candidate_track_ids)])}

Respond in JSON format:
{{
  "selected_indices": [1, 2, 3, 4, 5, 6, 7, 8],
  "reasoning": "Brief explanation of selection strategy"
}}

Select 5-8 indices from the list above."""

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse JSON response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                import json
                json_str = content[json_start:json_end]
                result = json.loads(json_str)

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
                
                # Return 5-8 seeds
                return selected_tracks[:8]

            else:
                logger.warning("Could not parse LLM seed selection response")
                return candidate_track_ids[:8]

        except Exception as e:
            logger.error(f"LLM seed selection failed: {str(e)}")
            # Fallback to top scored tracks
            return candidate_track_ids[:8]