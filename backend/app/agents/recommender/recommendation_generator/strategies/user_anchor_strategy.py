"""User anchor strategy for recommendations based on user-mentioned tracks.

Phase 2: New strategy that prioritizes tracks/artists explicitly mentioned by the user.
"""

import structlog
from typing import Any, Dict, List

from ....states.agent_state import AgentState
from .base_strategy import RecommendationStrategy

logger = structlog.get_logger(__name__)


class UserAnchorStrategy(RecommendationStrategy):
    """Strategy that generates recommendations based on user-mentioned tracks and artists.
    
    Phase 2: Prioritizes tracks that the user explicitly mentioned.
    
    This strategy:
    1. Gets user-mentioned tracks from SeedGathererAgent
    2. Uses Spotify's "Get Recommendations" API with ONLY those tracks as seeds
    3. Fetches artist's top tracks for mentioned artists
    4. Marks all results as high confidence
    """

    def __init__(self, spotify_service, reccobeat_service=None):
        """Initialize the user anchor strategy.

        Args:
            spotify_service: SpotifyService for API calls
            reccobeat_service: RecoBeatService (optional, for feature enrichment)
        """
        super().__init__(name="user_anchor")
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service

    async def generate_recommendations(
        self,
        state: AgentState,
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on user-mentioned tracks/artists.

        Args:
            state: Current agent state with user mentions
            target_count: Target number of recommendations

        Returns:
            List of recommendation dictionaries with high confidence scores
        """
        recommendations = []
        
        # Get user-mentioned tracks from metadata (set by SeedGathererAgent)
        user_mentioned_track_ids = state.metadata.get("user_mentioned_track_ids", [])
        user_mentioned_tracks_full = state.metadata.get("user_mentioned_tracks_full", [])
        intent_analysis = state.metadata.get("intent_analysis", {})
        user_mentioned_artists = intent_analysis.get("user_mentioned_artists", [])

        if not user_mentioned_track_ids and not user_mentioned_artists:
            logger.info("No user-mentioned tracks or artists, user anchor strategy skipped")
            return []

        logger.info(
            f"User anchor strategy: {len(user_mentioned_track_ids)} tracks, "
            f"{len(user_mentioned_artists)} artists"
        )

        # Get access token
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.warning("No access token for user anchor strategy")
            return []

        # PART 0: ALWAYS include the actual user-mentioned tracks themselves!
        if user_mentioned_tracks_full:
            for track in user_mentioned_tracks_full:
                track_id = track.get("id")
                track_name = track.get("name", "Unknown")
                artist_name = track.get("artist", "Unknown Artist")
                
                # Build Spotify URI if missing
                spotify_uri = track.get("uri")
                if not spotify_uri and track_id:
                    spotify_uri = f"spotify:track:{track_id}"
                
                # Try to get audio features if available
                audio_features = track.get("audio_features", {})
                
                # Build the recommendation with all required fields
                user_track_rec = {
                    "track_id": track_id,
                    "track_name": track_name,
                    "artists": [artist_name],
                    "spotify_uri": spotify_uri,
                    "confidence": 1.0,  # Maximum confidence - user explicitly requested this
                    "confidence_score": 1.0,  # Also set confidence_score for compatibility
                    "audio_features": audio_features,
                    "source": "anchor_track",  # CRITICAL: Must be anchor_track so it's recognized by the processor
                    "reasoning": f"User explicitly mentioned this track: '{track_name}' by {artist_name}",
                    "user_mentioned": True,
                    "protected": True,
                    "anchor_type": "user"
                }
                
                recommendations.append(user_track_rec)
                logger.info(
                    f"✓ Added user-mentioned track: '{track_name}' by {artist_name} "
                    f"(ID: {track_id}, URI: {spotify_uri}, source: anchor_track)"
                )
            logger.info(f"✓ Total {len(user_mentioned_tracks_full)} user-mentioned tracks added with full metadata")

        # PART 1: Get artists from user-mentioned tracks and fetch their top tracks
        if user_mentioned_track_ids:
            # Get full track info to extract artists
            track_based_recs = await self._get_tracks_from_same_artists(
                user_mentioned_tracks_full,
                access_token,
                target_count // 2 if user_mentioned_artists else target_count
            )
            recommendations.extend(track_based_recs)
            logger.info(f"Got {len(track_based_recs)} tracks from user-mentioned track artists")

        # PART 2: Get top tracks from user-mentioned artists
        if user_mentioned_artists:
            artist_based_recs = await self._get_top_tracks_from_artists(
                user_mentioned_artists,
                access_token,
                target_count // 2 if user_mentioned_track_ids else target_count
            )
            recommendations.extend(artist_based_recs)
            logger.info(f"Got {len(artist_based_recs)} top tracks from user-mentioned artists")

        # Mark all recommendations with high confidence
        # CRITICAL: Use "artist_discovery" as source so they're recognized by the processor
        for rec in recommendations:
            # If this is the actual user-mentioned track, it already has source="anchor_track"
            # Otherwise, set to artist_discovery so it's properly categorized
            if not rec.get("user_mentioned"):
                rec["source"] = "artist_discovery"
                rec["confidence_boost"] = 0.3  # Boost confidence for user mentions
                rec["user_mentioned_related"] = True
                # Set base confidence high since these are directly related to user intent
                if "confidence" not in rec:
                    rec["confidence"] = 0.85

        logger.info(f"User anchor strategy generated {len(recommendations)} recommendations")

        return recommendations[:target_count]

    async def _get_tracks_from_same_artists(
        self,
        user_mentioned_tracks: List[Dict[str, Any]],
        access_token: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get top tracks from artists of user-mentioned tracks.

        Args:
            user_mentioned_tracks: List of user-mentioned track dictionaries with artist info
            access_token: Spotify access token
            limit: Maximum number of tracks

        Returns:
            List of recommendation dictionaries
        """
        try:
            recommendations = []
            artist_ids_seen = set()
            
            # Extract unique artist IDs from user-mentioned tracks
            for track in user_mentioned_tracks:
                artist_id = track.get("artist_id")
                if artist_id and artist_id not in artist_ids_seen:
                    artist_ids_seen.add(artist_id)
            
            if not artist_ids_seen:
                return []
            
            # Get MORE tracks from user-mentioned artists (5-7 per artist instead of 2-3)
            tracks_per_artist = max(5, min(7, limit // len(artist_ids_seen)))
            
            logger.info(
                f"Getting {tracks_per_artist} tracks from each of {len(artist_ids_seen)} "
                f"user-mentioned track artists (limit: {limit})"
            )
            
            # Get top tracks for each artist
            for artist_id in artist_ids_seen:
                try:
                    top_tracks = await self.spotify_service.get_artist_top_tracks(
                        artist_id=artist_id,
                        access_token=access_token
                    )
                    
                    for track in top_tracks[:tracks_per_artist]:
                        if track.get("id"):
                            # Build proper artist list
                            artists = [a.get("name", "") for a in track.get("artists", [])]
                            
                            recommendations.append({
                                "track_id": track["id"],
                                "track_name": track.get("name", ""),
                                "artists": artists,  # Use artists list, not artist_name
                                "spotify_uri": track.get("uri"),
                                "popularity": track.get("popularity", 50),
                                "audio_features": {},
                                "confidence": 0.85  # High confidence - same artist as user mentioned
                            })
                            
                            logger.debug(
                                f"Added track from user-mentioned artist: '{track.get('name')}' by {', '.join(artists)}"
                            )
                except Exception as e:
                    logger.error(f"Error getting tracks for artist {artist_id}: {e}")
                    continue

            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Error getting tracks from same artists: {e}", exc_info=True)
            return []

    async def _get_top_tracks_from_artists(
        self,
        artist_names: List[str],
        access_token: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get top tracks from user-mentioned artists.

        Args:
            artist_names: List of artist names mentioned by user
            access_token: Spotify access token
            limit: Maximum number of tracks to return

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        try:
            tracks_per_artist = max(2, limit // len(artist_names)) if artist_names else limit

            for artist_name in artist_names:
                try:
                    # Search for the artist
                    artist_results = await self.spotify_service.search_spotify_artists(
                        access_token=access_token,
                        query=artist_name,
                        limit=1
                    )

                    if artist_results and len(artist_results) > 0:
                        artist = artist_results[0]
                        artist_id = artist.get("id")

                        if artist_id:
                            # Get artist's top tracks
                            top_tracks = await self.spotify_service.get_artist_top_tracks(
                                artist_id=artist_id,
                                access_token=access_token
                            )

                            # Add top tracks (limited per artist)
                            for track in top_tracks[:tracks_per_artist]:
                                if track.get("id"):
                                    # Extract all artists for consistency with other recommendation formats
                                    artists = [a.get("name", "") for a in track.get("artists", [])]
                                    
                                    recommendations.append({
                                        "track_id": track["id"],
                                        "track_name": track.get("name", ""),
                                        "artists": artists,  # Use artists list for consistency
                                        "spotify_uri": track.get("uri"),
                                        "popularity": track.get("popularity", 50),
                                        "audio_features": {},
                                        "confidence": 0.85  # Very high confidence for top tracks from mentioned artists
                                    })

                            logger.info(f"✓ Got {len(top_tracks[:tracks_per_artist])} top tracks from user-mentioned artist: {artist_name}")

                except Exception as e:
                    logger.error(f"Error getting top tracks for artist '{artist_name}': {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in _get_top_tracks_from_artists: {e}", exc_info=True)

        return recommendations[:limit]

