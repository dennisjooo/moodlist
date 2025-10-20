"""Main anchor selection engine coordinating all components."""

import structlog
from typing import Any, Dict, List, Optional, Tuple

from .track_processor import TrackProcessor
from .artist_processor import ArtistProcessor
from .llm_services import LLMServices
from .types import AnchorCandidate, AnchorSelectionStrategy

logger = structlog.get_logger(__name__)


class AnchorSelectionEngine:
    """Main engine for anchor track selection using modular components."""

    def __init__(
        self,
        spotify_service=None,
        reccobeat_service=None,
        llm: Optional[Any] = None
    ):
        """Initialize the anchor selection engine.

        Args:
            spotify_service: SpotifyService for track/artist search
            reccobeat_service: RecoBeatService for audio features
            llm: Language model for intelligent selection
        """
        self.spotify_service = spotify_service
        self.track_processor = TrackProcessor(reccobeat_service)
        self.artist_processor = ArtistProcessor(spotify_service, reccobeat_service)
        self.llm_services = LLMServices(llm)

    async def select_anchor_tracks(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str = "",
        artist_recommendations: Optional[List[str]] = None,
        mood_analysis: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Select anchor tracks using LLM-guided analysis.

        Args:
            genre_keywords: List of genre keywords to search
            target_features: Target audio features from mood analysis
            access_token: Spotify access token
            mood_prompt: Original user mood prompt for extracting track mentions
            artist_recommendations: List of artist names from mood analysis
            mood_analysis: Full mood analysis results for LLM context
            limit: Maximum number of anchor tracks to select (fallback if LLM doesn't specify)

        Returns:
            Tuple of (anchor_tracks_for_playlist, anchor_track_ids_for_reference)
        """
        if not self.spotify_service:
            logger.warning("No Spotify service available for anchor track selection")
            return [], []

        # Use LLM-driven selection if available, otherwise fallback to original logic
        if self.llm_services.llm and mood_analysis:
            return await self._llm_driven_anchor_selection(
                genre_keywords, target_features, access_token, mood_prompt,
                artist_recommendations or [], mood_analysis, limit
            )
        else:
            logger.info("No LLM available, using fallback anchor selection")
            return await self._fallback_anchor_selection(
                genre_keywords, target_features, access_token, mood_prompt,
                artist_recommendations or [], limit
            )

    async def _llm_driven_anchor_selection(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str,
        artist_recommendations: List[str],
        mood_analysis: Dict[str, Any],
        limit: int
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Use LLM analysis to determine and select optimal anchor tracks."""
        try:
            # Step 1: Get user-mentioned tracks (always priority)
            user_candidates = await self._get_user_mentioned_candidates(
                mood_prompt, artist_recommendations, access_token
            )
            logger.info(f"Found {len(user_candidates)} user-mentioned tracks as anchors")

            # Step 2: Get tracks from top recommended artists
            artist_candidates = await self.artist_processor.get_artist_based_candidates(
                mood_prompt, artist_recommendations, target_features, access_token, mood_analysis
            )
            logger.info(f"Found {len(artist_candidates)} artist-based track candidates")

            # Step 3: Get genre-based candidates for LLM to evaluate
            genre_candidates = []
            if genre_keywords:
                genre_candidates = await self._get_genre_based_candidates(
                    genre_keywords[:8], target_features, access_token, mood_prompt
                )
                logger.info(f"Found {len(genre_candidates)} genre-based track candidates")

            # Combine all candidates
            all_candidates = user_candidates + artist_candidates + genre_candidates

            if not all_candidates:
                logger.warning("No anchor track candidates found")
                return [], []

            # Step 4: LLM-based filtering for cultural/linguistic relevance
            all_candidates = await self.llm_services.filter_tracks_by_relevance(
                all_candidates, mood_prompt, mood_analysis
            )

            if not all_candidates:
                logger.warning("No anchor track candidates after LLM filtering")
                return [], []

            # Step 5: Use LLM to determine optimal selection strategy
            strategy = await self.llm_services.get_anchor_selection_strategy(
                mood_prompt, mood_analysis, genre_keywords, target_features, all_candidates
            )

            anchor_count = strategy.anchor_count or limit
            selection_criteria = strategy.selection_criteria or {}

            # Step 6: Use LLM to score all candidates
            scored_candidates = await self.llm_services.score_candidates(
                all_candidates, target_features, mood_analysis, selection_criteria
            )

            # Step 7: Use LLM to finalize selection
            selected_tracks, selected_ids = await self.llm_services.finalize_selection(
                scored_candidates, anchor_count, mood_analysis
            )

            logger.info(
                f"LLM-selected {len(selected_tracks)} anchor tracks from {len(all_candidates)} candidates"
            )

            return selected_tracks, selected_ids

        except Exception as e:
            logger.error(f"LLM-driven anchor selection failed: {e}")
            # Fallback to original logic
            return await self._fallback_anchor_selection(
                genre_keywords, target_features, access_token, mood_prompt,
                artist_recommendations, limit
            )

    async def _fallback_anchor_selection(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str,
        artist_recommendations: List[str],
        limit: int
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Fallback anchor selection using original hard-coded logic."""
        anchor_candidates = []

        # PRIORITY 1: Add user-mentioned tracks with highest priority
        user_candidates = await self._get_user_mentioned_candidates(
            mood_prompt, artist_recommendations, access_token
        )
        anchor_candidates.extend(user_candidates)
        logger.info(f"Found {len(user_candidates)} user-mentioned tracks as anchors")

        # PRIORITY 2: Add tracks from mentioned artists
        if artist_recommendations:
            # Create minimal mood_analysis for fallback mode
            fallback_mood_analysis = {
                'mood_interpretation': '',
                'genre_keywords': genre_keywords,
                'artist_recommendations': artist_recommendations
            }
            artist_candidates = await self.artist_processor.get_artist_based_candidates(
                mood_prompt, artist_recommendations, target_features, access_token, fallback_mood_analysis
            )
            anchor_candidates.extend(artist_candidates)
            logger.info(f"Found {len(artist_candidates)} artist-based tracks as anchors")

        # PRIORITY 3: Add genre-based tracks
        if not genre_keywords and (user_candidates or artist_candidates):
            logger.info("No genre keywords, but using user/artist-mentioned tracks as anchors")
        else:
            # Use top 5 genres for better diversity (increased from 3)
            genre_candidates = await self._get_genre_based_candidates(
                genre_keywords[:5], target_features, access_token, mood_prompt
            )
            anchor_candidates.extend(genre_candidates)

        if not anchor_candidates:
            logger.warning("No anchor track candidates found")
            return [], []

        # Sort and select top anchors
        return self._select_top_anchors(anchor_candidates, limit)

    async def _get_user_mentioned_candidates(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from user-mentioned tracks."""
        user_mentioned_tracks = await self._find_user_mentioned_tracks(
            mood_prompt, artist_recommendations, access_token
        )

        candidates = []
        for track in user_mentioned_tracks:
            if not track.get('id'):
                continue

            # Get audio features if available
            features = {}
            if self.track_processor.reccobeat_service:
                try:
                    features_map = await self.track_processor.get_track_features_batch([track['id']])
                    features = features_map.get(track['id'], {})
                    track['audio_features'] = features
                except Exception as e:
                    logger.warning(f"Failed to get features for user-mentioned track: {e}")

            # Mark track metadata for protection
            track['user_mentioned'] = True  # CRITICAL: Never filter this track
            track['anchor_type'] = 'user'  # User anchor (guaranteed inclusion)
            track['protected'] = True  # Protected from quality filtering

            candidates.append({
                'track': track,
                'score': 1.0,  # Highest priority for user-mentioned tracks
                'confidence': 1.0,  # Maximum confidence
                'features': features,
                'source': 'user_mentioned',
                'anchor_type': 'user',
                'user_mentioned': True,
                'protected': True
            })

        return candidates

    async def _find_user_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Extract and search for specific tracks mentioned by the user."""
        if not mood_prompt:
            return []

        user_tracks = []

        # Use LLM if available for intelligent extraction
        if self.llm_services.llm:
            track_artist_pairs = await self.llm_services.extract_user_mentioned_tracks(
                mood_prompt, artist_recommendations
            )
        else:
            # Fallback to simple pattern matching
            track_artist_pairs = self.llm_services.simple_extract_mentioned_tracks(
                mood_prompt, artist_recommendations
            )

        # Search for each extracted track
        for track_name, artist_name in track_artist_pairs[:5]:  # Limit to 5 tracks
            try:
                # Search for track with artist context
                search_query = f"{track_name} {artist_name}" if artist_name else track_name
                logger.info(f"Searching for user-mentioned track: '{search_query}'")

                tracks = await self.spotify_service.search_spotify_tracks(
                    access_token=access_token,
                    query=search_query,
                    limit=3
                )

                if tracks:
                    # Take the first result (most relevant)
                    best_match = tracks[0]
                    logger.info(
                        f"Found user-mentioned track: '{best_match.get('name')}' by "
                        f"{', '.join([a.get('name', '') for a in best_match.get('artists', [])])}"
                    )
                    user_tracks.append(best_match)

            except Exception as e:
                logger.warning(f"Failed to search for user-mentioned track '{track_name}': {e}")
                continue

        return user_tracks

    async def _get_genre_based_candidates(
        self,
        genres: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from genre-based track search."""
        candidates = []

        for genre in genres:
            try:
                logger.info(f"Searching anchor tracks for genre: {genre}")
                tracks = await self.spotify_service.search_spotify_tracks(
                    access_token=access_token,
                    query=f"genre:{genre}",
                    limit=10
                )

                genre_candidates = await self._score_and_create_candidates(
                    tracks, target_features, genre, mood_prompt, genres
                )
                candidates.extend(genre_candidates)

            except Exception as e:
                logger.error(f"Failed to search anchor tracks for genre '{genre}': {e}")
                continue

        return candidates

    async def _score_and_create_candidates(
        self,
        tracks: List[Dict[str, Any]],
        target_features: Dict[str, Any],
        genre: str,
        mood_prompt: str = "",
        genre_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Score tracks and create anchor candidates."""
        if not tracks:
            return []

        candidates = []

        # Try to get audio features if RecoBeat service available
        if self.track_processor.reccobeat_service:
            track_ids = [track['id'] for track in tracks if track.get('id')]

            try:
                features_map = await self.track_processor.get_track_features_batch(track_ids)

                # Score tracks by feature match
                for track in tracks:
                    track_id = track.get('id')
                    if not track_id:
                        continue

                    features = features_map.get(track_id, {})
                    if features:
                        track['audio_features'] = features

                    candidate = self.track_processor.create_candidate_from_track(
                        track, target_features, genre, mood_prompt,
                        genre_keywords or [], features, f"genre_{genre}"
                    )
                    if candidate:
                        candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Failed to get audio features for anchor tracks: {e}")
                # Add tracks with default scores
                for track in tracks:
                    if track.get('id'):
                        candidate = self.track_processor.create_candidate_from_track(
                            track, target_features, genre, mood_prompt, genre_keywords or []
                        )
                        if candidate:
                            candidates.append(candidate)
        else:
            # No RecoBeat service, add tracks with default scores
            for track in tracks:
                if track.get('id'):
                    candidate = self.track_processor.create_candidate_from_track(
                        track, target_features, genre, mood_prompt, genre_keywords or []
                    )
                    if candidate:
                        candidates.append(candidate)

        return candidates

    def _select_top_anchors(
        self,
        candidates: List[Dict[str, Any]],
        limit: int
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Sort candidates by score and select top anchors."""
        candidates.sort(key=lambda x: x['score'], reverse=True)
        top_anchors = candidates[:limit]

        anchor_tracks = [a['track'] for a in top_anchors]
        anchor_ids = [a['track']['id'] for a in top_anchors]

        avg_score = sum(a['score'] for a in top_anchors) / len(top_anchors)
        logger.info(
            f"Selected {len(anchor_tracks)} anchor tracks from {len(candidates)} candidates "
            f"(avg score: {avg_score:.2f})"
        )

        return anchor_tracks, anchor_ids