"""Service for enriching recommendations with missing Spotify data."""

import structlog
from typing import List, Dict, Any, Optional
from ....states.agent_state import TrackRecommendation
from ....tools.spotify_service import SpotifyService

logger = structlog.get_logger(__name__)


class TrackEnrichmentService:
    """Service for finding and enriching tracks with missing Spotify URIs."""

    def __init__(self, spotify_service: SpotifyService):
        """Initialize the track enrichment service.

        Args:
            spotify_service: Service for Spotify API operations
        """
        self.spotify_service = spotify_service

    async def enrich_recommendations(
        self,
        recommendations: List[TrackRecommendation],
        access_token: str
    ) -> List[TrackRecommendation]:
        """Enrich recommendations by finding missing Spotify URIs.

        Args:
            recommendations: List of track recommendations to enrich
            access_token: Spotify access token for API calls

        Returns:
            Updated list of recommendations with enriched Spotify data
        """
        enriched_recommendations = []
        enrichment_stats = {
            "total": len(recommendations),
            "already_valid": 0,
            "enriched": 0,
            "failed": 0,
            "removed": 0
        }

        for rec in recommendations:
            # Check if track needs enrichment
            needs_enrichment = (
                not rec.spotify_uri or
                rec.spotify_uri == "null" or
                "Unknown Artist" in rec.artists or
                rec.track_name == "Unknown Track"
            )

            if not needs_enrichment:
                enrichment_stats["already_valid"] += 1
                enriched_recommendations.append(rec)
                continue

            logger.info(
                f"Enriching track: '{rec.track_name}' by {', '.join(rec.artists)} "
                f"(missing URI: {not rec.spotify_uri})"
            )

            # Try to find the track on Spotify
            enriched_rec = await self._enrich_track(rec, access_token)

            if enriched_rec:
                enrichment_stats["enriched"] += 1
                enriched_recommendations.append(enriched_rec)
            else:
                # Track enrichment failed - decide whether to keep or remove
                if rec.user_mentioned or rec.protected:
                    # Keep protected tracks even if we can't find them
                    logger.warning(
                        f"Could not enrich protected track: '{rec.track_name}' - keeping anyway"
                    )
                    enrichment_stats["failed"] += 1
                    enriched_recommendations.append(rec)
                else:
                    # Remove tracks that can't be enriched and aren't protected
                    logger.warning(
                        f"Removing unenriched track: '{rec.track_name}' "
                        f"(not found on Spotify)"
                    )
                    enrichment_stats["removed"] += 1

        logger.info(
            f"Enrichment complete: {enrichment_stats['enriched']} enriched, "
            f"{enrichment_stats['already_valid']} already valid, "
            f"{enrichment_stats['failed']} failed (kept), "
            f"{enrichment_stats['removed']} removed"
        )

        return enriched_recommendations

    async def _enrich_track(
        self,
        rec: TrackRecommendation,
        access_token: str
    ) -> Optional[TrackRecommendation]:
        """Enrich a single track recommendation with Spotify data.

        Args:
            rec: Track recommendation to enrich
            access_token: Spotify access token

        Returns:
            Enriched TrackRecommendation or None if not found
        """
        # Build search query
        search_query = self._build_search_query(rec)

        if not search_query:
            logger.warning(f"Cannot build search query for track: {rec.track_name}")
            return None

        try:
            # Search Spotify for the track
            search_results = await self.spotify_service.search_spotify_tracks(
                access_token=access_token,
                query=search_query,
                limit=5
            )

            if not search_results:
                logger.warning(f"No Spotify results for query: '{search_query}'")
                return None

            # Find best match
            best_match = self._find_best_match(rec, search_results)

            if not best_match:
                logger.warning(f"No suitable match found for: '{rec.track_name}'")
                return None

            # Create enriched recommendation
            return self._create_enriched_recommendation(rec, best_match)

        except Exception as e:
            logger.error(f"Error enriching track '{rec.track_name}': {e}", exc_info=True)
            return None

    def _build_search_query(self, rec: TrackRecommendation) -> Optional[str]:
        """Build a Spotify search query from recommendation data.

        Args:
            rec: Track recommendation

        Returns:
            Search query string or None if insufficient data
        """
        track_name = rec.track_name
        artists = rec.artists

        # Skip if we don't have basic info
        if track_name == "Unknown Track" or not track_name:
            return None

        # Filter out "Unknown Artist"
        valid_artists = [a for a in artists if a and a != "Unknown Artist"]

        if valid_artists:
            # Include artist in search for better accuracy
            artist_str = " ".join(valid_artists[:2])  # Use max 2 artists
            return f"track:{track_name} artist:{artist_str}"
        else:
            # Search by track name only
            return f"track:{track_name}"

    def _find_best_match(
        self,
        rec: TrackRecommendation,
        search_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching track from search results.

        Args:
            rec: Original track recommendation
            search_results: List of Spotify search results

        Returns:
            Best matching track or None
        """
        if not search_results:
            return None

        # If we have artist info, try to match by artist
        valid_artists = [a.lower() for a in rec.artists if a and a != "Unknown Artist"]

        if valid_artists:
            # Try to find a track with matching artist
            for track in search_results:
                track_artists = [
                    artist.get("name", "").lower()
                    for artist in track.get("artists", [])
                ]

                # Check if any artist matches
                for rec_artist in valid_artists:
                    for track_artist in track_artists:
                        # Fuzzy match - check if artist names are similar
                        if (
                            rec_artist in track_artist or
                            track_artist in rec_artist or
                            self._artist_names_similar(rec_artist, track_artist)
                        ):
                            logger.info(
                                f"Found match: '{track.get('name')}' by "
                                f"{', '.join([a.get('name') for a in track.get('artists', [])])} "
                                f"(matched artist: {rec_artist} ≈ {track_artist})"
                            )
                            return track

        # If no artist match or no artist info, return first result
        # (Spotify ranks by relevance, so first result is usually best)
        first_result = search_results[0]
        logger.info(
            f"Using first search result: '{first_result.get('name')}' by "
            f"{', '.join([a.get('name') for a in first_result.get('artists', [])])}"
        )
        return first_result

    def _artist_names_similar(self, name1: str, name2: str) -> bool:
        """Check if two artist names are similar enough to be considered a match.

        Args:
            name1: First artist name (lowercase)
            name2: Second artist name (lowercase)

        Returns:
            True if names are similar
        """
        # Remove common words that might differ
        common_words = {"the", "a", "an", "&", "and"}

        words1 = set(name1.split()) - common_words
        words2 = set(name2.split()) - common_words

        # Check if there's significant overlap
        if not words1 or not words2:
            return False

        intersection = words1 & words2
        min_length = min(len(words1), len(words2))

        # Consider similar if more than 50% of words match
        return len(intersection) / min_length >= 0.5

    def _create_enriched_recommendation(
        self,
        original_rec: TrackRecommendation,
        spotify_track: Dict[str, Any]
    ) -> TrackRecommendation:
        """Create an enriched recommendation from Spotify track data.

        Args:
            original_rec: Original recommendation
            spotify_track: Spotify track data

        Returns:
            Enriched TrackRecommendation
        """
        # Extract Spotify data
        track_id = spotify_track.get("id", original_rec.track_id)
        track_name = spotify_track.get("name", original_rec.track_name)
        spotify_uri = spotify_track.get("uri") or spotify_track.get("spotify_uri")
        artists = [
            artist.get("name", "Unknown Artist")
            for artist in spotify_track.get("artists", [])
        ]

        # Preserve original metadata but update with Spotify data
        return TrackRecommendation(
            track_id=track_id,
            track_name=track_name,
            artists=artists if artists else original_rec.artists,
            spotify_uri=spotify_uri,
            confidence_score=original_rec.confidence_score,
            audio_features=original_rec.audio_features,
            reasoning=f"{original_rec.reasoning} (enriched from Spotify)",
            source=original_rec.source,
            user_mentioned=original_rec.user_mentioned,
            anchor_type=original_rec.anchor_type,
            protected=original_rec.protected
        )

