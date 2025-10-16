"""Audio enricher for enhancing tracks with audio features from external services."""

import structlog
from typing import Any, Dict, List

logger = structlog.get_logger(__name__)


class AudioEnricher:
    """Handles enrichment of tracks with audio features from external services."""

    def __init__(self, reccobeat_service=None):
        """Initialize the audio enricher.

        Args:
            reccobeat_service: Service for RecoBeat API operations (for audio features)
        """
        self.reccobeat_service = reccobeat_service

    async def enrich_tracks_with_features(
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