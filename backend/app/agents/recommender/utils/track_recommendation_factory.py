"""Factory for creating TrackRecommendation objects from various data sources."""

from typing import Any, Dict, List, Optional

import structlog

from ...states.agent_state import TrackRecommendation

logger = structlog.get_logger(__name__)


class TrackRecommendationFactory:
    """Factory for creating standardized TrackRecommendation objects."""

    @staticmethod
    def from_spotify_track(
        track_data: Dict[str, Any],
        source: str = "spotify",
        confidence_score: float = 0.5,
        reasoning: Optional[str] = None,
    ) -> Optional[TrackRecommendation]:
        """Create TrackRecommendation from Spotify track data.

        Args:
            track_data: Spotify track response data
            source: Source identifier (e.g., "artist_discovery", "spotify")
            confidence_score: Confidence score for the recommendation
            reasoning: Explanation for why this track was recommended

        Returns:
            TrackRecommendation object or None if invalid data
        """
        try:
            track_id = track_data.get("id")
            if not track_id:
                logger.debug("Skipping track without ID")
                return None

            # Extract artist information
            artists = track_data.get("artists", [])
            artist_names = [artist.get("name", "Unknown Artist") for artist in artists]

            # Extract track information
            track_name = track_data.get("name", "Unknown Track")
            spotify_uri = track_data.get("uri") or track_data.get("spotify_uri")

            # Extract audio features if available
            audio_features = TrackRecommendationFactory._extract_audio_features(
                track_data
            )

            return TrackRecommendation(
                track_id=track_id,
                track_name=track_name,
                artists=artist_names,
                spotify_uri=spotify_uri,
                confidence_score=confidence_score,
                audio_features=audio_features,
                reasoning=reasoning or f"Recommended from {source}",
                source=source,
            )

        except Exception as e:
            logger.warning(
                f"Failed to create TrackRecommendation from Spotify data: {e}"
            )
            return None

    @staticmethod
    def from_reccobeat_response(
        response_data: Dict[str, Any],
        source: str = "reccobeat",
        reasoning: Optional[str] = None,
    ) -> Optional[TrackRecommendation]:
        """Create TrackRecommendation from RecoBeat API response.

        Args:
            response_data: RecoBeat API response data
            source: Source identifier
            reasoning: Explanation for the recommendation

        Returns:
            TrackRecommendation object or None if invalid data
        """
        try:
            track_id = response_data.get("track_id")
            if not track_id:
                logger.debug("Skipping RecoBeat response without track_id")
                return None

            # Use confidence_score from response or default
            confidence_score = response_data.get("confidence_score", 0.5)

            # Extract or create reasoning
            reasoning = (
                reasoning
                or response_data.get("reasoning")
                or f"Recommended by RecoBeat from {source}"
            )

            return TrackRecommendation(
                track_id=track_id,
                track_name=response_data.get("track_name", "Unknown Track"),
                artists=response_data.get("artists", ["Unknown Artist"]),
                spotify_uri=response_data.get("spotify_uri"),
                confidence_score=confidence_score,
                audio_features=response_data.get("audio_features"),
                reasoning=reasoning,
                source=source,
            )

        except Exception as e:
            logger.warning(
                f"Failed to create TrackRecommendation from RecoBeat data: {e}"
            )
            return None

    @staticmethod
    def from_artist_top_track(
        track_data: Dict[str, Any],
        artist_id: str,
        confidence_score: float = 0.7,
        reasoning: Optional[str] = None,
    ) -> Optional[TrackRecommendation]:
        """Create TrackRecommendation from artist's top track data.

        Args:
            track_data: Spotify artist top track data
            artist_id: Spotify artist ID
            confidence_score: Confidence score (higher for artist tracks)
            reasoning: Explanation for the recommendation

        Returns:
            TrackRecommendation object or None if invalid data
        """
        reasoning = reasoning or f"Top track from mood-matched artist {artist_id}"

        return TrackRecommendationFactory.from_spotify_track(
            track_data=track_data,
            source="artist_discovery",
            confidence_score=confidence_score,
            reasoning=reasoning,
        )

    @staticmethod
    def from_seed_based_generation(
        response_data: Dict[str, Any],
        seed_tracks: List[str],
        reasoning: Optional[str] = None,
    ) -> Optional[TrackRecommendation]:
        """Create TrackRecommendation from seed-based generation.

        Args:
            response_data: API response data
            seed_tracks: List of seed track IDs used for generation
            reasoning: Explanation for the recommendation

        Returns:
            TrackRecommendation object or None if invalid data
        """
        reasoning = (
            reasoning
            or f"Mood-based recommendation using seeds: {', '.join(seed_tracks[:3])}"
        )

        return TrackRecommendationFactory.from_reccobeat_response(
            response_data=response_data, source="reccobeat", reasoning=reasoning
        )

    @staticmethod
    def _extract_audio_features(track_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract audio features from track data.

        Args:
            track_data: Track data that may contain audio features

        Returns:
            Audio features dictionary or None
        """
        # Try different possible locations for audio features
        audio_features = (
            track_data.get("audio_features") or track_data.get("features") or {}
        )

        # If we have any features, return them; otherwise return None
        return audio_features if audio_features else None

    @staticmethod
    def create_batch(
        track_data_list: List[Dict[str, Any]], factory_method: str = "spotify", **kwargs
    ) -> List[TrackRecommendation]:
        """Create multiple TrackRecommendation objects from a list of track data.

        Args:
            track_data_list: List of track data dictionaries
            factory_method: Factory method to use ("spotify", "reccobeat", "artist")
            **kwargs: Additional arguments to pass to the factory method

        Returns:
            List of TrackRecommendation objects (filtering out None values)
        """
        recommendations = []

        for track_data in track_data_list:
            try:
                if factory_method == "spotify":
                    rec = TrackRecommendationFactory.from_spotify_track(
                        track_data, **kwargs
                    )
                elif factory_method == "reccobeat":
                    rec = TrackRecommendationFactory.from_reccobeat_response(
                        track_data, **kwargs
                    )
                elif factory_method == "artist":
                    rec = TrackRecommendationFactory.from_artist_top_track(
                        track_data, **kwargs
                    )
                else:
                    logger.warning(f"Unknown factory method: {factory_method}")
                    continue

                if rec:
                    recommendations.append(rec)

            except Exception as e:
                logger.warning(f"Failed to create recommendation from track data: {e}")
                continue

        return recommendations
