"""Scoring engine for confidence calculation and mood matching."""

import structlog
from typing import Any, Dict, Optional

from ....states.agent_state import AgentState

logger = structlog.get_logger(__name__)


class ScoringEngine:
    """Handles confidence scoring and mood matching calculations."""

    def calculate_confidence_score(
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
        # Check if RecoBeat provided a score/rating
        existing_score = self._get_existing_score(recommendation_data)
        if existing_score is not None:
            return existing_score

        # Fallback calculation using multiple factors
        base_score = self._calculate_base_score(recommendation_data, state)
        penalty = self._calculate_penalties(recommendation_data, state)
        source_multiplier = self._get_source_multiplier(recommendation_data)

        final_score = (base_score - penalty) * source_multiplier
        return min(max(final_score, 0.0), 1.0)

    def _get_existing_score(self, recommendation_data: Dict[str, Any]) -> Optional[float]:
        """Extract existing score from recommendation data if available.

        Args:
            recommendation_data: Raw recommendation data

        Returns:
            Normalized score (0-1) or None if no existing score
        """
        if "score" in recommendation_data:
            # RecoBeat returns scores typically 0-100, normalize to 0-1
            return min(recommendation_data["score"] / 100.0, 1.0)

        if "rating" in recommendation_data:
            # If rating is already 0-1, use it directly
            rating = recommendation_data["rating"]
            return rating if rating <= 1.0 else rating / 100.0

        if "confidence" in recommendation_data:
            return min(recommendation_data["confidence"], 1.0)

        return None

    def _calculate_base_score(
        self,
        recommendation_data: Dict[str, Any],
        state: AgentState
    ) -> float:
        """Calculate base confidence score from popularity and mood matching.

        Args:
            recommendation_data: Raw recommendation data
            state: Current agent state

        Returns:
            Base score before penalties
        """
        base_score = 0.6  # Higher base score

        # Factor in track popularity if available
        popularity = recommendation_data.get("popularity", 0)
        if popularity > 0:
            # Scale popularity contribution
            popularity_factor = min(popularity / 100.0, 1.0)
            base_score += (0.15 * popularity_factor)

        # Factor in audio features match with mood
        target_features = state.metadata.get("target_features", {})
        audio_features = recommendation_data.get("audio_features")

        if target_features and audio_features:
            mood_match_score = self._calculate_mood_match(audio_features, target_features)
            base_score += (0.4 * mood_match_score)  # Increased weight for mood matching
        elif target_features:
            # Boost for having target features even without audio features
            base_score += 0.1

        return base_score

    def _calculate_penalties(
        self,
        recommendation_data: Dict[str, Any],
        state: AgentState
    ) -> float:
        """Calculate penalties for feature violations.

        Args:
            recommendation_data: Raw recommendation data
            state: Current agent state

        Returns:
            Total penalty to subtract from score
        """
        target_features = state.metadata.get("target_features", {})
        audio_features = recommendation_data.get("audio_features")

        if not target_features or not audio_features:
            return 0.0

        penalty = 0.0

        # Penalize high speechiness if target is low
        if "speechiness" in target_features and "speechiness" in audio_features:
            target_speech = target_features["speechiness"]
            actual_speech = audio_features["speechiness"]
            if target_speech < 0.2 and actual_speech > 0.3:
                penalty += 0.15 * (actual_speech - 0.3)

        # Penalize high liveness if target is low
        if "liveness" in target_features and "liveness" in audio_features:
            target_live = target_features["liveness"]
            actual_live = audio_features["liveness"]
            if target_live < 0.3 and actual_live > 0.5:
                penalty += 0.1 * (actual_live - 0.5)

        return penalty

    def _get_source_multiplier(self, recommendation_data: Dict[str, Any]) -> float:
        """Get source-based multiplier for score adjustment.

        Args:
            recommendation_data: Raw recommendation data

        Returns:
            Multiplier to apply to final score
        """
        # Apply source penalty - RecoBeat has circular dependency bias
        # (recommendations are generated using target features, so they score high but may be irrelevant)
        if recommendation_data.get("source") == "reccobeat":
            return 0.85  # 15% penalty for RecoBeat bias

        return 1.0

    def _calculate_mood_match(
        self,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well audio features match target mood features.

        Args:
            audio_features: Track audio features
            target_features: Target mood features

        Returns:
            Match score (0-1)
        """
        if not audio_features or not target_features:
            return 0.5

        # Compare key features
        feature_keys = ["energy", "valence", "danceability", "acousticness"]
        matches = 0
        total_features = 0

        for key in feature_keys:
            if key in audio_features and key in target_features:
                track_value = audio_features[key]
                target_value = target_features[key]

                # Handle range values as string (e.g., "0.8-1.0")
                if isinstance(target_value, str):
                    try:
                        if '-' in target_value:
                            parts = target_value.split('-')
                            if len(parts) == 2:
                                min_val = float(parts[0])
                                max_val = float(parts[1])
                                target_mid = (min_val + max_val) / 2
                                # Calculate similarity (closer = better)
                                similarity = 1.0 - abs(track_value - target_mid)
                                matches += similarity
                            else:
                                # Single value as string
                                target_num = float(target_value)
                                similarity = 1.0 - abs(track_value - target_num)
                                matches += similarity
                        else:
                            # Single value as string
                            target_num = float(target_value)
                            similarity = 1.0 - abs(track_value - target_num)
                            matches += similarity
                        total_features += 1
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse target value '{target_value}' for {key}: {e}")
                        continue
                # Handle range values as list (e.g., [0.8, 1.0])
                elif isinstance(target_value, list) and len(target_value) == 2:
                    target_mid = sum(target_value) / 2
                    # Calculate similarity (closer = better)
                    similarity = 1.0 - abs(track_value - target_mid)
                    matches += similarity
                    total_features += 1
                # Handle numeric values
                elif isinstance(target_value, (int, float)):
                    similarity = 1.0 - abs(track_value - target_value)
                    matches += similarity
                    total_features += 1

        return matches / total_features if total_features > 0 else 0.5

    def calculate_track_cohesion(
        self,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track's audio features match target mood features.

        Args:
            audio_features: Track's audio features
            target_features: Target mood features

        Returns:
            Cohesion score (0-1)
        """
        if not audio_features or not target_features:
            return 0.5

        scores = []

        # Define tolerance thresholds
        tolerance_thresholds = {
            "energy": 0.3,
            "valence": 0.3,
            "danceability": 0.3,
            "acousticness": 0.4,
            "instrumentalness": 0.25,
            "speechiness": 0.25,
            "tempo": 40.0,
            "loudness": 6.0,
            "liveness": 0.4,
            "popularity": 30
        }

        for feature_name, target_value in target_features.items():
            if feature_name not in audio_features:
                continue

            actual_value = audio_features[feature_name]
            tolerance = tolerance_thresholds.get(feature_name)

            if tolerance is None:
                continue

            # Convert target value to single number if it's a range
            if isinstance(target_value, list) and len(target_value) == 2:
                target_single = sum(target_value) / 2
            elif isinstance(target_value, (int, float)):
                target_single = float(target_value)
            else:
                continue

            # Calculate difference and score
            difference = abs(actual_value - target_single)
            match_score = max(0.0, 1.0 - (difference / tolerance))
            scores.append(match_score)

        # Return average match score
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5
