"""Audio features handling for track analysis."""

import logging
from typing import Any, Dict, Optional

from ...tools.reccobeat_service import RecoBeatService

logger = logging.getLogger(__name__)


class AudioFeaturesHandler:
    """Handles audio features retrieval and processing."""

    def __init__(self, reccobeat_service: RecoBeatService):
        """Initialize the audio features handler.

        Args:
            reccobeat_service: Service for RecoBeat API operations
        """
        self.reccobeat_service = reccobeat_service

    async def get_complete_audio_features(
        self,
        track_id: str,
        existing_features: Optional[Dict[str, Any]] = None
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
            "acousticness", "danceability", "energy", "instrumentalness",
            "key", "liveness", "loudness", "mode", "speechiness",
            "tempo", "valence", "popularity"
        }

        if required_features.issubset(complete_features.keys()):
            return complete_features

        try:
            # Fetch complete audio features from RecoBeat API
            audio_features_result = await self.reccobeat_service.get_tracks_audio_features([track_id])

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
                    "popularity": api_features.get("popularity")
                }

                # Update with API features (only add non-None values)
                for feature_name, feature_value in feature_mapping.items():
                    if feature_value is not None:
                        complete_features[feature_name] = feature_value

                logger.info(f"Enhanced audio features for track {track_id}: got {len(complete_features)} features")

        except Exception as e:
            logger.warning(f"Failed to get complete audio features for track {track_id}: {e}")
            # Continue with existing features if API call fails

        return complete_features
