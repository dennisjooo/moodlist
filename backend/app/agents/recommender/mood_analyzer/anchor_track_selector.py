"""Anchor track selector for finding high-quality genre-specific tracks."""

import structlog
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ..utils.llm_response_parser import LLMResponseParser
from .prompts import get_track_extraction_prompt

logger = structlog.get_logger(__name__)


class AnchorTrackSelector:
    """Selects anchor tracks from genre searches for feature reference and playlist inclusion."""

    def __init__(self, spotify_service=None, reccobeat_service=None, llm: Optional[BaseLanguageModel] = None):
        """Initialize the anchor track selector.
        
        Args:
            spotify_service: SpotifyService for track search
            reccobeat_service: RecoBeatService for audio features
            llm: Language model for extracting user-mentioned tracks/artists
        """
        self.spotify_service = spotify_service
        self.reccobeat_service = reccobeat_service
        self.llm = llm

    async def select_anchor_tracks(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str = "",
        artist_recommendations: List[str] = None,
        limit: int = 5
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Select anchor tracks from user-mentioned tracks and top genre results.
        
        Args:
            genre_keywords: List of genre keywords to search
            target_features: Target audio features from mood analysis
            access_token: Spotify access token
            mood_prompt: Original user mood prompt for extracting track mentions
            artist_recommendations: List of artist names from mood analysis
            limit: Maximum number of anchor tracks to select
            
        Returns:
            Tuple of (anchor_tracks_for_playlist, anchor_track_ids_for_reference)
        """
        if not self.spotify_service:
            logger.warning("No Spotify service available for anchor track selection")
            return [], []

        anchor_candidates = []
        
        # PRIORITY 1: Add user-mentioned tracks with highest priority
        user_candidates = await self._get_user_mentioned_candidates(
            mood_prompt,
            artist_recommendations or [],
            access_token
        )
        anchor_candidates.extend(user_candidates)
        logger.info(f"Found {len(user_candidates)} user-mentioned tracks as anchors")
        
        # PRIORITY 2: Add genre-based tracks
        if not genre_keywords and user_candidates:
            logger.info("No genre keywords, but using user-mentioned tracks as anchors")
        else:
            genre_candidates = await self._get_genre_based_candidates(
                genre_keywords[:3],
                target_features,
                access_token
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
        """Get anchor candidates from user-mentioned tracks.
        
        Args:
            mood_prompt: User's mood prompt
            artist_recommendations: List of artist names
            access_token: Spotify access token
            
        Returns:
            List of anchor candidate dictionaries with user-mentioned tracks
        """
        user_mentioned_tracks = await self._find_user_mentioned_tracks(
            mood_prompt,
            artist_recommendations,
            access_token
        )
        
        candidates = []
        for track in user_mentioned_tracks:
            if not track.get('id'):
                continue
                
            # Get audio features if available
            features = {}
            if self.reccobeat_service:
                try:
                    features_map = await self.reccobeat_service.get_tracks_audio_features([track['id']])
                    features = features_map.get(track['id'], {})
                    track['audio_features'] = features
                except Exception as e:
                    logger.warning(f"Failed to get features for user-mentioned track: {e}")
            
            candidates.append({
                'track': track,
                'score': 1.0,  # Highest priority for user-mentioned tracks
                'features': features,
                'source': 'user_mentioned'
            })
        
        return candidates

    async def _get_genre_based_candidates(
        self,
        genres: List[str],
        target_features: Dict[str, Any],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from genre-based track search.
        
        Args:
            genres: List of genre keywords to search
            target_features: Target audio features for scoring
            access_token: Spotify access token
            
        Returns:
            List of anchor candidate dictionaries from genre searches
        """
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
                    tracks,
                    target_features,
                    genre
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
        genre: str
    ) -> List[Dict[str, Any]]:
        """Score tracks and create anchor candidates.
        
        Args:
            tracks: List of track dictionaries from Spotify
            target_features: Target audio features for scoring
            genre: Genre name for metadata
            
        Returns:
            List of anchor candidate dictionaries
        """
        if not tracks:
            return []
        
        candidates = []
        
        # Try to get audio features if RecoBeat service available
        if self.reccobeat_service:
            track_ids = [track['id'] for track in tracks if track.get('id')]
            
            try:
                features_map = await self.reccobeat_service.get_tracks_audio_features(track_ids)
                
                # Score tracks by feature match
                for track in tracks:
                    track_id = track.get('id')
                    if not track_id:
                        continue
                    
                    features = features_map.get(track_id, {})
                    if features:
                        score = self._calculate_feature_match(features, target_features)
                        track['audio_features'] = features
                    else:
                        score = 0.6
                    
                    candidates.append({
                        'track': track,
                        'score': score,
                        'features': features,
                        'genre': genre
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to get audio features for anchor tracks: {e}")
                # Add tracks with default scores
                for track in tracks:
                    if track.get('id'):
                        candidates.append({
                            'track': track,
                            'score': 0.6,
                            'features': {},
                            'genre': genre
                        })
        else:
            # No RecoBeat service, add tracks with default scores
            for track in tracks:
                if track.get('id'):
                    candidates.append({
                        'track': track,
                        'score': 0.65,
                        'features': {},
                        'genre': genre
                    })
        
        return candidates

    def _select_top_anchors(
        self,
        candidates: List[Dict[str, Any]],
        limit: int
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Sort candidates by score and select top anchors.
        
        Args:
            candidates: List of anchor candidate dictionaries
            limit: Maximum number of anchors to select
            
        Returns:
            Tuple of (anchor_tracks, anchor_track_ids)
        """
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

    def _calculate_feature_match(
        self,
        track_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well track features match target features.
        
        Args:
            track_features: Audio features of the track
            target_features: Target audio features from mood analysis
            
        Returns:
            Match score (0-1)
        """
        if not track_features or not target_features:
            return 0.5
        
        scores = []
        
        # Key features to match
        feature_keys = ["energy", "valence", "danceability", "acousticness", "instrumentalness"]
        
        for key in feature_keys:
            if key not in track_features or key not in target_features:
                continue
            
            track_value = track_features[key]
            target_value = target_features[key]
            
            # Handle range values (e.g., [0.7, 1.0])
            if isinstance(target_value, list) and len(target_value) == 2:
                target_mid = sum(target_value) / 2
                # Calculate similarity (closer = better)
                difference = abs(track_value - target_mid)
                similarity = max(0.0, 1.0 - difference)
                scores.append(similarity)
            # Handle single numeric values
            elif isinstance(target_value, (int, float)):
                difference = abs(track_value - target_value)
                similarity = max(0.0, 1.0 - difference)
                scores.append(similarity)
        
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5

    async def _find_user_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        access_token: str
    ) -> List[Dict[str, Any]]:
        """Extract and search for specific tracks mentioned by the user using LLM.
        
        Uses LLM to intelligently extract track names and artists mentioned in the prompt,
        then searches Spotify for those tracks.
        
        Args:
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis
            access_token: Spotify access token
            
        Returns:
            List of track dictionaries for user-mentioned tracks
        """
        if not mood_prompt:
            return []
        
        user_tracks = []
        
        # Use LLM if available for intelligent extraction
        if self.llm:
            track_artist_pairs = await self._llm_extract_mentioned_tracks(mood_prompt, artist_recommendations)
        else:
            # Fallback to simple pattern matching
            track_artist_pairs = self._simple_extract_mentioned_tracks(mood_prompt, artist_recommendations)
        
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

    async def _llm_extract_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str]
    ) -> List[tuple[str, str]]:
        """Use LLM to extract specific tracks and artists mentioned by the user.
        
        Args:
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis
            
        Returns:
            List of (track_name, artist_name) tuples
        """
        try:
            prompt = get_track_extraction_prompt(mood_prompt, artist_recommendations)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            
            # Parse using centralized parser utility
            result = LLMResponseParser.extract_json_from_response(response)
            
            mentioned_tracks = result.get("mentioned_tracks", [])
            reasoning = result.get("reasoning", "")
            
            if mentioned_tracks:
                logger.info(f"LLM extracted {len(mentioned_tracks)} mentioned tracks: {reasoning}")
                return [(t.get("track_name", ""), t.get("artist_name", "")) for t in mentioned_tracks]
            else:
                logger.info("LLM found no specific tracks mentioned in prompt")
                return []
                
        except Exception as e:
            logger.error(f"LLM track extraction failed: {e}")
            return []

    def _simple_extract_mentioned_tracks(
        self,
        mood_prompt: str,
        artist_recommendations: List[str]
    ) -> List[tuple[str, str]]:
        """Simple fallback pattern matching for track extraction.
        
        Args:
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis
            
        Returns:
            List of (track_name, artist_name) tuples
        """
        track_hints = []
        
        # Look for "especially" followed by track names
        if "especially" in mood_prompt.lower():
            parts = mood_prompt.split("especially")
            if len(parts) > 1:
                after_especially = parts[1].strip()
                # Split by "and" or ","
                if "," in after_especially:
                    tracks = after_especially.split(",")
                elif " and " in after_especially.lower():
                    tracks = after_especially.split(" and ")
                else:
                    tracks = [after_especially]
                
                # Clean up track names
                primary_artist = artist_recommendations[0] if artist_recommendations else ""
                for track in tracks[:3]:
                    track_name = track.split(".")[0].split("?")[0].strip().rstrip(",;:")
                    if track_name and len(track_name) > 2:
                        track_hints.append((track_name, primary_artist))
        
        return track_hints

