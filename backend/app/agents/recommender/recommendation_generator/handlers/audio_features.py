"""Audio features handling for track analysis."""

from typing import Any, Dict, List, Optional, Tuple

import structlog

from ....tools.reccobeat_service import RecoBeatService

logger = structlog.get_logger(__name__)

DEFAULT_AUDIO_FEATURES: Dict[str, Any] = {
    "acousticness": 0.5,
    "danceability": 0.5,
    "energy": 0.5,
    "instrumentalness": 0.0,
    "key": 0,  # Default to C major when key is unknown
    "liveness": 0.2,
    "loudness": -8.0,
    "mode": 1,
    "speechiness": 0.05,
    "tempo": 120.0,
    "valence": 0.5,
    "popularity": 50,
}


class AudioFeaturesHandler:
    """Handles audio features retrieval and processing."""

    def __init__(self, reccobeat_service: RecoBeatService):
        """Initialize the audio features handler.

        Args:
            reccobeat_service: Service for RecoBeat API operations
        """
        self.reccobeat_service = reccobeat_service

    async def get_batch_complete_audio_features(
        self, track_data: List[Tuple[str, Optional[Dict[str, Any]]]]
    ) -> Dict[str, Dict[str, Any]]:
        """Get complete audio features for multiple tracks using RecoBeat API.

        Args:
            track_data: List of tuples (track_id, existing_features)

        Returns:
            Dictionary mapping track IDs to complete audio features
        """
        required_features = {
            "acousticness",
            "danceability",
            "energy",
            "instrumentalness",
            "key",
            "liveness",
            "loudness",
            "mode",
            "speechiness",
            "tempo",
            "valence",
            "popularity",
        }

        results = {}
        tracks_needing_api = []

        # First pass: check which tracks need API calls
        for track_id, existing_features in track_data:
            complete_features = {}
            if existing_features:
                complete_features.update(existing_features)

            # If we already have all features, skip API call
            if required_features.issubset(complete_features.keys()):
                results[track_id] = complete_features
            else:
                tracks_needing_api.append(track_id)
                results[track_id] = complete_features

        # Batch fetch for tracks that need API calls
        if tracks_needing_api:
            try:
                audio_features_result = (
                    await self.reccobeat_service.get_tracks_audio_features(
                        tracks_needing_api
                    )
                )

                successful_fetches = 0
                for track_id in tracks_needing_api:
                    if track_id in audio_features_result:
                        api_features = audio_features_result[track_id]

                        # Map API response to expected feature names and merge with existing
                        feature_mapping = {
                            "acousticness": api_features.get("acousticness"),
                            "danceability": api_features.get("danceability"),
                            "energy": api_features.get("energy"),
                            "instrumentalness": api_features.get("instrumentalness"),
                            "key": api_features.get("key"),
                            "liveness": api_features.get("liveness"),
                            "loudness": api_features.get("loudness"),
                            "mode": api_features.get("mode"),
                            "speechiness": api_features.get("speechiness"),
                            "tempo": api_features.get("tempo"),
                            "valence": api_features.get("valence"),
                            "popularity": api_features.get("popularity"),
                        }

                        # Update with API features (only add non-None values)
                        for feature_name, feature_value in feature_mapping.items():
                            if feature_value is not None:
                                results[track_id][feature_name] = feature_value

                        successful_fetches += 1
                    else:
                        # Track not found in RecoBeat - use defaults if needed
                        logger.debug(
                            f"Track {track_id} not found in RecoBeat, using defaults if needed"
                        )
                        # Only add missing features, don't override existing
                        for (
                            feature_name,
                            default_value,
                        ) in DEFAULT_AUDIO_FEATURES.items():
                            if feature_name not in results[track_id]:
                                results[track_id][feature_name] = default_value

                logger.info(
                    f"Enhanced audio features for {successful_fetches}/{len(tracks_needing_api)} tracks "
                    f"({len(tracks_needing_api) - successful_fetches} using defaults)"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to get batch audio features: {e}, using defaults for missing tracks"
                )
                # Apply defaults to all tracks that need features
                for track_id in tracks_needing_api:
                    if track_id in results:
                        for (
                            feature_name,
                            default_value,
                        ) in DEFAULT_AUDIO_FEATURES.items():
                            if feature_name not in results[track_id]:
                                results[track_id][feature_name] = default_value

        # Ensure every track has a full feature set by applying defaults for missing values
        for track_id, feature_map in results.items():
            for feature_name, default_value in DEFAULT_AUDIO_FEATURES.items():
                if feature_name not in feature_map or feature_map[feature_name] is None:
                    feature_map[feature_name] = default_value

        return results

    async def get_complete_audio_features(
        self, track_id: str, existing_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get complete audio features for a track using RecoBeat API.

        Args:
            track_id: The track ID to get features for
            existing_features: Any existing features from the recommendation

        Returns:
            Complete audio features dictionary with all 12 features
        """
        complete_features = {}

        # Start with existing features if available
        if existing_features:
            complete_features.update(existing_features)

        # If we already have all features, return them
        required_features = {
            "acousticness",
            "danceability",
            "energy",
            "instrumentalness",
            "key",
            "liveness",
            "loudness",
            "mode",
            "speechiness",
            "tempo",
            "valence",
            "popularity",
        }

        if required_features.issubset(complete_features.keys()):
            return complete_features

        try:
            # Fetch complete audio features from RecoBeat API
            audio_features_result = (
                await self.reccobeat_service.get_tracks_audio_features([track_id])
            )

            if track_id in audio_features_result:
                api_features = audio_features_result[track_id]

                # Map API response to expected feature names and merge with existing
                feature_mapping = {
                    "acousticness": api_features.get("acousticness"),
                    "danceability": api_features.get("danceability"),
                    "energy": api_features.get("energy"),
                    "instrumentalness": api_features.get("instrumentalness"),
                    "key": api_features.get("key"),
                    "liveness": api_features.get("liveness"),
                    "loudness": api_features.get("loudness"),
                    "mode": api_features.get("mode"),
                    "speechiness": api_features.get("speechiness"),
                    "tempo": api_features.get("tempo"),
                    "valence": api_features.get("valence"),
                    "popularity": api_features.get("popularity"),
                }

                # Update with API features (only add non-None values)
                for feature_name, feature_value in feature_mapping.items():
                    if feature_value is not None:
                        complete_features[feature_name] = feature_value

                logger.info(
                    f"Enhanced audio features for track {track_id}: got {len(complete_features)} features"
                )
            else:
                # Track not found in RecoBeat - use defaults
                logger.debug(f"Track {track_id} not found in RecoBeat, using defaults")
                for feature_name, default_value in DEFAULT_AUDIO_FEATURES.items():
                    if feature_name not in complete_features:
                        complete_features[feature_name] = default_value

        except Exception as e:
            logger.warning(
                f"Failed to get complete audio features for track {track_id}: {e}, using defaults"
            )
            # Apply defaults for missing features
            for feature_name, default_value in DEFAULT_AUDIO_FEATURES.items():
                if feature_name not in complete_features:
                    complete_features[feature_name] = default_value

        # Ensure full feature set with defaults
        for feature_name, default_value in DEFAULT_AUDIO_FEATURES.items():
            if (
                feature_name not in complete_features
                or complete_features[feature_name] is None
            ):
                complete_features[feature_name] = default_value

        return complete_features
