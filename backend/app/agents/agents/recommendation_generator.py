"""Recommendation generator agent for creating mood-based track recommendations."""

import logging
import random
from typing import Any, Dict, List, Optional

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
from ..tools.reccobeat_service import RecoBeatService


logger = logging.getLogger(__name__)


class RecommendationGeneratorAgent(BaseAgent):
    """Agent for generating mood-based track recommendations."""

    def __init__(
        self,
        reccobeat_service: RecoBeatService,
        max_recommendations: int = 30,
        diversity_factor: float = 0.7,
        verbose: bool = False
    ):
        """Initialize the recommendation generator agent.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            max_recommendations: Maximum number of recommendations to generate
            diversity_factor: Factor for ensuring diversity in recommendations (0-1)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="recommendation_generator",
            description="Generates sophisticated mood-based track recommendations using RecoBeat API",
            verbose=verbose
        )

        self.reccobeat_service = reccobeat_service
        self.max_recommendations = max_recommendations
        self.diversity_factor = diversity_factor

    async def execute(self, state: AgentState) -> AgentState:
        """Execute recommendation generation.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with recommendations
        """
        try:
            logger.info(f"Generating recommendations for mood: {state.mood_prompt}")

            # Check if we have seed tracks
            if not state.seed_tracks:
                logger.warning("No seed tracks available for recommendations")
                # Try to generate recommendations without seeds as fallback
                recommendations = await self._generate_fallback_recommendations(state)
            else:
                # Generate recommendations using seeds and mood analysis
                recommendations = await self._generate_mood_based_recommendations(state)

            # Filter and rank recommendations
            filtered_recommendations = self._filter_and_rank_recommendations(
                recommendations,
                state.mood_analysis
            )

            # Ensure diversity in recommendations
            diverse_recommendations = self._ensure_diversity(filtered_recommendations)

            # Update state with recommendations
            for rec in diverse_recommendations[:self.max_recommendations]:
                state.add_recommendation(rec)

            state.current_step = "recommendations_generated"
            state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS

            # Store metadata
            state.metadata["total_recommendations_generated"] = len(diverse_recommendations)
            state.metadata["final_recommendation_count"] = len(state.recommendations)
            state.metadata["recommendation_strategy"] = "mood_based_with_seeds"

            logger.info(f"Generated {len(state.recommendations)} final recommendations")

        except Exception as e:
            logger.error(f"Error in recommendation generation: {str(e)}", exc_info=True)
            state.set_error(f"Recommendation generation failed: {str(e)}")

        return state

    async def _generate_mood_based_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations based on mood analysis and seeds.

        Args:
            state: Current agent state

        Returns:
            List of raw recommendations from RecoBeat
        """
        all_recommendations = []

        # Split seeds into smaller chunks for multiple API calls
        seed_chunks = self._chunk_seeds(state.seed_tracks, chunk_size=3)

        # Get mood-based features
        mood_features = self._extract_mood_features(state.mood_analysis)

        for chunk in seed_chunks:
            try:
                # Get recommendations for this seed chunk
                chunk_recommendations = await self.reccobeat_service.get_track_recommendations(
                    seeds=chunk,
                    size=15,  # Get more per chunk for filtering
                    **mood_features
                )

                # Convert to TrackRecommendation objects
                for rec_data in chunk_recommendations:
                    try:
                        recommendation = TrackRecommendation(
                            track_id=rec_data.get("id", ""),
                            track_name=rec_data.get("track_name", "Unknown Track"),
                            artists=rec_data.get("artists", ["Unknown Artist"]),
                            spotify_uri=rec_data.get("spotify_uri"),
                            confidence_score=self._calculate_confidence_score(rec_data, state),
                            audio_features=rec_data.get("audio_features"),
                            reasoning=f"Mood-based recommendation using seeds: {', '.join(chunk)}",
                            source="reccobeat"
                        )
                        all_recommendations.append(recommendation)

                    except Exception as e:
                        logger.warning(f"Failed to create recommendation object: {e}")
                        continue

                # Add some delay between API calls to respect rate limits
                import asyncio
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating recommendations for seed chunk {chunk}: {e}")
                continue

        logger.info(f"Generated {len(all_recommendations)} raw recommendations from {len(seed_chunks)} seed chunks")

        return [rec.dict() for rec in all_recommendations]

    async def _generate_fallback_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when no seeds are available.

        Args:
            state: Current agent state

        Returns:
            List of fallback recommendations
        """
        logger.info("Generating fallback recommendations without seeds")

        # Use mood-based search with artist keywords
        if state.mood_analysis and state.mood_analysis.get("search_keywords"):
            keywords = state.mood_analysis["search_keywords"][:3]  # Use top 3 keywords

            # Search for artists matching mood keywords
            matching_artists = await self.reccobeat_service.search_artists_by_mood(
                keywords,
                limit=5
            )

            if matching_artists:
                # Use found artists as seeds for recommendations
                artist_ids = [artist["id"] for artist in matching_artists if artist.get("id")]

                if artist_ids:
                    fallback_recommendations = await self.reccobeat_service.get_track_recommendations(
                        seeds=artist_ids[:3],  # Use up to 3 artists as seeds
                        size=20
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

    def _extract_mood_features(self, mood_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract audio features from mood analysis.

        Args:
            mood_analysis: Mood analysis results

        Returns:
            Dictionary of audio features for RecoBeat API
        """
        features = {}

        if not mood_analysis or not mood_analysis.get("target_features"):
            return features

        target_features = mood_analysis["target_features"]

        # Map mood analysis features to RecoBeat API parameters
        feature_mapping = {
            "energy": "energy",
            "valence": "valence",
            "danceability": "danceability",
            "acousticness": "acousticness",
            "instrumentalness": "instrumentalness",
            "tempo": "tempo",
            "key": "key",
            "mode": "mode",
            "speechiness": "speechiness",
            "liveness": "liveness",
            "loudness": "loudness"
        }

        for mood_feature, api_param in feature_mapping.items():
            if mood_feature in target_features:
                value = target_features[mood_feature]

                # Handle range values (take midpoint)
                if isinstance(value, list) and len(value) == 2:
                    features[api_param] = sum(value) / 2
                else:
                    features[api_param] = value

        # Set feature weight for stronger mood influence
        features["feature_weight"] = 3.0

        return features

    def _calculate_confidence_score(
        self,
        recommendation_data: Dict[str, Any],
        state: AgentState
    ) -> float:
        """Calculate confidence score for a recommendation.

        Args:
            recommendation_data: Raw recommendation data
            state: Current agent state

        Returns:
            Confidence score (0-1)
        """
        base_score = 0.5

        # Factor in track popularity if available
        popularity = recommendation_data.get("popularity", 50)
        popularity_factor = popularity / 100.0

        # Weight popularity moderately
        confidence_score = base_score + (0.3 * popularity_factor)

        # Boost confidence if we have strong mood analysis
        if state.mood_analysis and state.mood_analysis.get("target_features"):
            confidence_score += 0.2

        return min(confidence_score, 1.0)

    def _filter_and_rank_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None
    ) -> List[TrackRecommendation]:
        """Filter and rank recommendations based on mood analysis.

        Args:
            recommendations: Raw recommendations
            mood_analysis: Mood analysis results

        Returns:
            Filtered and ranked TrackRecommendation objects
        """
        if not recommendations:
            return []

        # Convert to TrackRecommendation objects
        rec_objects = []
        for rec_data in recommendations:
            try:
                rec_obj = TrackRecommendation(
                    track_id=rec_data.get("id", ""),
                    track_name=rec_data.get("track_name", "Unknown Track"),
                    artists=rec_data.get("artists", ["Unknown Artist"]),
                    spotify_uri=rec_data.get("spotify_uri"),
                    confidence_score=rec_data.get("confidence_score", 0.5),
                    audio_features=rec_data.get("audio_features"),
                    reasoning=rec_data.get("reasoning", "Mood-based recommendation"),
                    source=rec_data.get("source", "reccobeat")
                )
                rec_objects.append(rec_obj)

            except Exception as e:
                logger.warning(f"Failed to create recommendation object: {e}")
                continue

        # Sort by confidence score
        rec_objects.sort(key=lambda x: x.confidence_score, reverse=True)

        # Apply mood-based filtering if available
        if mood_analysis and mood_analysis.get("target_features"):
            rec_objects = self._apply_mood_filtering(rec_objects, mood_analysis)

        return rec_objects

    def _apply_mood_filtering(
        self,
        recommendations: List[TrackRecommendation],
        mood_analysis: Dict[str, Any]
    ) -> List[TrackRecommendation]:
        """Apply mood-based filtering to recommendations.

        Args:
            recommendations: List of recommendations to filter
            mood_analysis: Mood analysis results

        Returns:
            Filtered recommendations
        """
        if not mood_analysis.get("target_features"):
            return recommendations

        target_features = mood_analysis["target_features"]
        filtered_recommendations = []

        for rec in recommendations:
            # Simple filtering based on available features
            # In a real implementation, you might use audio features for more sophisticated filtering

            # For now, we'll keep all recommendations but could add filtering logic here
            # based on the target_features from mood analysis

            filtered_recommendations.append(rec)

        return filtered_recommendations

    def _ensure_diversity(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Ensure diversity in recommendations to avoid repetition.

        Args:
            recommendations: List of recommendations to diversify

        Returns:
            Diversified recommendations
        """
        if not recommendations:
            return recommendations

        # Simple diversity approach: reduce weight of artists that appear multiple times
        artist_counts = {}
        diversified_recommendations = []

        for rec in recommendations:
            # Count artist occurrences
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

            # Reduce confidence score for artists that appear multiple times
            diversity_penalty = 0
            for artist in rec.artists:
                if artist_counts[artist] > 1:
                    diversity_penalty += 0.1 * (artist_counts[artist] - 1)

            # Apply diversity penalty
            adjusted_confidence = rec.confidence_score - diversity_penalty
            adjusted_confidence = max(adjusted_confidence, 0.1)  # Minimum confidence

            # Create new recommendation with adjusted confidence
            diversified_rec = TrackRecommendation(
                track_id=rec.track_id,
                track_name=rec.track_name,
                artists=rec.artists,
                spotify_uri=rec.spotify_uri,
                confidence_score=adjusted_confidence,
                audio_features=rec.audio_features,
                reasoning=f"{rec.reasoning} (diversity-adjusted)",
                source=rec.source
            )

            diversified_recommendations.append(diversified_rec)

        # Re-sort by adjusted confidence
        diversified_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

        return diversified_recommendations