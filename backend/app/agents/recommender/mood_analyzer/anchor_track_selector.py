"""Anchor track selector for finding high-quality genre-specific tracks."""

import structlog
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ..utils.llm_response_parser import LLMResponseParser
from .prompts import (
    get_track_extraction_prompt,
    get_anchor_strategy_prompt,
    get_anchor_scoring_prompt,
    get_anchor_finalization_prompt,
    get_batch_track_filter_prompt,
    get_batch_artist_validation_prompt,
)

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
        mood_analysis: Dict[str, Any] = None,
        limit: int = 5
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Select anchor tracks using LLM-guided analysis instead of hard-coded logic.

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
        if self.llm and mood_analysis:
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

    async def _get_genre_based_candidates(
        self,
        genres: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from genre-based track search.
        
        Args:
            genres: List of genre keywords to search
            target_features: Target audio features for scoring
            access_token: Spotify access token
            mood_prompt: Original user prompt for context-aware filtering
            
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
                    genre,
                    mood_prompt,
                    genres
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
        genre_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Score tracks and create anchor candidates.
        
        Args:
            tracks: List of track dictionaries from Spotify
            target_features: Target audio features for scoring
            genre: Genre name for metadata
            mood_prompt: Original user prompt for context-aware filtering
            genre_keywords: All genre keywords for context
            
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
                        feature_score = self._calculate_feature_match(features, target_features)
                        track['audio_features'] = features
                    else:
                        feature_score = 0.6
                    
                    # Phase 3: Weight popularity for better mainstream alignment
                    popularity = track.get('popularity', 50) / 100.0  # Normalize to 0-1
                    final_score = feature_score * 0.7 + popularity * 0.3
                    
                    # Phase 3: Context-aware language filtering
                    # Only penalize if language doesn't match user intent
                    artist_names = [a.get('name', '') for a in track.get('artists', [])]
                    track_script = self._detect_track_script(track.get('name', ''), artist_names)
                    
                    if self._should_apply_language_penalty(
                        track_script,
                        mood_prompt,
                        genre_keywords or []
                    ):
                        final_score *= 0.5  # Penalty for language mismatch
                        logger.debug(
                            f"Applied language mismatch penalty to '{track.get('name')}' "
                            f"by {', '.join(artist_names)} (script: {track_script})"
                        )
                    
                    # Mark genre-based anchor metadata (can be filtered if poor fit)
                    track['user_mentioned'] = False
                    track['anchor_type'] = 'genre'
                    track['protected'] = False  # Genre anchors can be filtered
                    
                    candidates.append({
                        'track': track,
                        'score': final_score,
                        'confidence': 0.85,  # Standard confidence for genre anchors
                        'features': features,
                        'genre': genre,
                        'anchor_type': 'genre',
                        'user_mentioned': False,
                        'protected': False
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to get audio features for anchor tracks: {e}")
                # Add tracks with default scores
                for track in tracks:
                    if track.get('id'):
                        track['user_mentioned'] = False
                        track['anchor_type'] = 'genre'
                        track['protected'] = False
                        candidates.append({
                            'track': track,
                            'score': 0.6,
                            'confidence': 0.85,
                            'features': {},
                            'genre': genre,
                            'anchor_type': 'genre',
                            'user_mentioned': False,
                            'protected': False
                        })
        else:
            # No RecoBeat service, add tracks with default scores
            for track in tracks:
                if track.get('id'):
                    track['user_mentioned'] = False
                    track['anchor_type'] = 'genre'
                    track['protected'] = False
                    candidates.append({
                        'track': track,
                        'score': 0.65,
                        'confidence': 0.85,
                        'features': {},
                        'genre': genre,
                        'anchor_type': 'genre',
                        'user_mentioned': False,
                        'protected': False
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

    def _detect_track_script(self, track_name: str, artist_names: List[str]) -> str:
        """Detect the writing system/script used in track and artist names.
        
        Args:
            track_name: Name of the track
            artist_names: List of artist names
            
        Returns:
            Script type: 'latin', 'cjk', 'arabic', 'hebrew', 'thai', 'cyrillic'
        """
        text = f"{track_name} {' '.join(artist_names)}"
        
        # Check for various scripts (order matters - check more specific first)
        if any('\u4e00' <= char <= '\u9fff' or  # Chinese
                '\u3040' <= char <= '\u309f' or  # Hiragana
                '\u30a0' <= char <= '\u30ff' or  # Katakana
                '\uac00' <= char <= '\ud7af'     # Korean
                for char in text):
            return 'cjk'
        
        if any('\u0600' <= char <= '\u06ff' for char in text):
            return 'arabic'
        
        if any('\u0590' <= char <= '\u05ff' for char in text):
            return 'hebrew'
        
        if any('\u0e00' <= char <= '\u0e7f' for char in text):
            return 'thai'
        
        if any('\u0400' <= char <= '\u04ff' for char in text):
            return 'cyrillic'
        
        # Default to Latin (English, Spanish, French, German, etc.)
        return 'latin'
    
    def _should_apply_language_penalty(
        self,
        track_script: str,
        mood_prompt: str,
        genre_keywords: List[str]
    ) -> bool:
        """Determine if a language penalty should be applied based on context.
        
        Only penalize tracks if their language clearly doesn't match user intent.
        
        Args:
            track_script: Detected script of the track ('cjk', 'arabic', 'latin', etc.)
            mood_prompt: Original user prompt
            genre_keywords: List of genre keywords from mood analysis
            
        Returns:
            True if penalty should be applied, False otherwise
        """
        # If track is Latin script (English/European languages), never penalize
        # This covers the vast majority of music and avoids false positives
        if track_script == 'latin':
            return False
        
        # Check if user explicitly requested non-English music
        prompt_lower = mood_prompt.lower()
        genres_lower = ' '.join(genre_keywords).lower()
        
        # Language/region indicators in prompt or genres
        non_english_indicators = {
            'cjk': ['korean', 'k-pop', 'kpop', 'japanese', 'j-pop', 'jpop', 'chinese', 
                    'c-pop', 'cpop', 'mandarin', 'cantonese', 'anime', 'asian'],
            'arabic': ['arabic', 'middle eastern', 'persian', 'turkish'],
            'hebrew': ['hebrew', 'israeli'],
            'thai': ['thai', 'southeast asian'],
            'cyrillic': ['russian', 'cyrillic', 'slavic']
        }
        
        # If user explicitly wants this language/region, don't penalize
        indicators = non_english_indicators.get(track_script, [])
        for indicator in indicators:
            if indicator in prompt_lower or indicator in genres_lower:
                logger.debug(
                    f"Not applying language penalty - user requested {indicator} music"
                )
                return False
        
        # If we got here: track is non-Latin and user didn't request it
        # Apply penalty (likely a cultural mismatch)
        return True

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

    async def _llm_driven_anchor_selection(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str,
        artist_recommendations: List[str],
        mood_analysis: Dict[str, Any],
        limit: int
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Use LLM analysis to determine and select optimal anchor tracks.

        Args:
            genre_keywords: List of genre keywords to search
            target_features: Target audio features from mood analysis
            access_token: Spotify access token
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis
            mood_analysis: Full mood analysis results
            limit: Fallback limit if LLM doesn't specify

        Returns:
            Tuple of (anchor_tracks_for_playlist, anchor_track_ids_for_reference)
        """
        try:
            # Step 1: Get user-mentioned tracks (always priority)
            user_candidates = await self._get_user_mentioned_candidates(
                mood_prompt, artist_recommendations, access_token
            )
            logger.info(f"Found {len(user_candidates)} user-mentioned tracks as anchors")

            # Step 2: Get tracks from top recommended artists (especially those mentioned in prompt)
            artist_candidates = await self._get_artist_based_candidates(
                mood_prompt, artist_recommendations, target_features, access_token, mood_analysis
            )
            logger.info(f"Found {len(artist_candidates)} artist-based track candidates")

            # Step 3: Get genre-based candidates for LLM to evaluate
            genre_candidates = []
            if genre_keywords:
                genre_candidates = await self._get_genre_based_candidates(
                    genre_keywords[:8],  # Allow more candidates for LLM to choose from
                    target_features,
                    access_token,
                    mood_prompt
                )
                logger.info(f"Found {len(genre_candidates)} genre-based track candidates")

            # Combine all candidates
            all_candidates = user_candidates + artist_candidates + genre_candidates

            if not all_candidates:
                logger.warning("No anchor track candidates found")
                return [], []

            # Step 3: LLM-based filtering for cultural/linguistic relevance
            all_candidates = await self._filter_tracks_by_relevance(
                all_candidates, mood_prompt, mood_analysis
            )

            if not all_candidates:
                logger.warning("No anchor track candidates after LLM filtering")
                return [], []

            # Step 4: Use LLM to determine optimal selection strategy
            strategy = await self._get_anchor_selection_strategy(
                mood_prompt, mood_analysis, genre_keywords, target_features, all_candidates
            )

            anchor_count = strategy.get('anchor_count', limit)
            selection_criteria = strategy.get('selection_criteria', {})

            # Step 5: Use LLM to score all candidates
            scored_candidates = await self._llm_score_candidates(
                all_candidates, target_features, mood_analysis, selection_criteria
            )

            # Step 6: Use LLM to finalize selection
            selected_tracks, selected_ids = await self._llm_finalize_selection(
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

    async def _get_anchor_selection_strategy(
        self,
        mood_prompt: str,
        mood_analysis: Dict[str, Any],
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to determine the optimal strategy for anchor track selection.

        Args:
            mood_prompt: User's mood prompt
            mood_analysis: Full mood analysis
            genre_keywords: Genre keywords
            target_features: Target audio features
            candidates: Available track candidates

        Returns:
            Strategy dictionary with anchor count and selection criteria
        """
        try:
            prompt = get_anchor_strategy_prompt(
                mood_prompt, mood_analysis, genre_keywords, target_features, candidates
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            logger.info("LLM determined anchor selection strategy")
            return result

        except Exception as e:
            logger.warning(f"Failed to get LLM anchor strategy: {e}")
            # Return default strategy
            return {
                "anchor_count": 5,
                "selection_criteria": {
                    "prioritize_user_mentioned": True,
                    "feature_weights": {
                        "danceability": 1.0,
                        "energy": 0.9,
                        "valence": 0.8,
                        "tempo": 0.9,
                        "instrumentalness": 0.7
                    },
                    "popularity_weight": 0.3,
                    "genre_diversity": True
                }
            }

    async def _llm_score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        target_features: Dict[str, Any],
        mood_analysis: Dict[str, Any],
        selection_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to score anchor track candidates.

        Args:
            candidates: List of track candidates
            target_features: Target audio features
            selection_criteria: Criteria from strategy analysis

        Returns:
            List of candidates with LLM-assigned scores
        """
        try:
            prompt = get_anchor_scoring_prompt(
                candidates, target_features, selection_criteria
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            track_scores = result.get('track_scores', [])

            # Attach scores back to candidates
            scored_candidates = []
            for score_data in track_scores:
                track_index = score_data.get('track_index', 0)
                if 0 <= track_index < len(candidates):
                    candidate = candidates[track_index].copy()
                    candidate['llm_score'] = score_data.get('score', 0.5)
                    candidate['llm_confidence'] = score_data.get('confidence', 0.5)
                    candidate['llm_reasoning'] = score_data.get('reasoning', '')
                    scored_candidates.append(candidate)

            logger.info(f"LLM scored {len(scored_candidates)} anchor candidates")
            return scored_candidates

        except Exception as e:
            logger.warning(f"Failed to get LLM candidate scores: {e}")
            # Return candidates with default scores
            for candidate in candidates:
                candidate['llm_score'] = 0.6
                candidate['llm_confidence'] = 0.5
                candidate['llm_reasoning'] = 'Default scoring due to LLM failure'
            return candidates

    async def _llm_finalize_selection(
        self,
        scored_candidates: List[Dict[str, Any]],
        target_count: int,
        mood_analysis: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Use LLM to finalize the selection of anchor tracks.

        Args:
            scored_candidates: Candidates with LLM scores
            target_count: Target number of anchors
            mood_analysis: Mood analysis context

        Returns:
            Tuple of (selected_tracks, selected_track_ids)
        """
        try:
            prompt = get_anchor_finalization_prompt(
                scored_candidates, target_count, mood_analysis
            )

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            selected_indices = result.get('selected_indices', [])
            selection_reasoning = result.get('selection_reasoning', '')

            # Extract selected tracks and IDs
            selected_tracks = []
            selected_ids = []

            for idx in selected_indices:
                if 0 <= idx < len(scored_candidates):
                    candidate = scored_candidates[idx]
                    track = candidate.get('track', {})

                    # Add LLM metadata
                    track['llm_score'] = candidate.get('llm_score', 0.5)
                    track['llm_reasoning'] = candidate.get('llm_reasoning', '')
                    track['anchor_type'] = candidate.get('anchor_type', 'llm_selected')
                    track['protected'] = candidate.get('protected', False)

                    selected_tracks.append(track)
                    if track.get('id'):
                        selected_ids.append(track['id'])

            logger.info(
                f"LLM finalized selection of {len(selected_tracks)} anchor tracks: {selection_reasoning}"
            )

            return selected_tracks, selected_ids

        except Exception as e:
            logger.warning(f"Failed to finalize LLM selection: {e}")
            # Fallback: sort by LLM score and take top N
            scored_candidates.sort(key=lambda x: x.get('llm_score', 0), reverse=True)
            top_candidates = scored_candidates[:target_count]

            selected_tracks = [c.get('track', {}) for c in top_candidates]
            selected_ids = [t.get('id') for t in selected_tracks if t.get('id')]

            return selected_tracks, selected_ids

    async def _fallback_anchor_selection(
        self,
        genre_keywords: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_prompt: str,
        artist_recommendations: List[str],
        limit: int
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Fallback anchor selection using original hard-coded logic.

        Args:
            genre_keywords: List of genre keywords to search
            target_features: Target audio features from mood analysis
            access_token: Spotify access token
            mood_prompt: Original user mood prompt
            artist_recommendations: List of artist names from mood analysis
            limit: Maximum number of anchor tracks to select

        Returns:
            Tuple of (anchor_tracks_for_playlist, anchor_track_ids_for_reference)
        """
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
            artist_candidates = await self._get_artist_based_candidates(
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
                genre_keywords[:5],
                target_features,
                access_token,
                mood_prompt
            )
            anchor_candidates.extend(genre_candidates)

        if not anchor_candidates:
            logger.warning("No anchor track candidates found")
            return [], []

        # Sort and select top anchors
        return self._select_top_anchors(anchor_candidates, limit)

    async def _get_artist_based_candidates(
        self,
        mood_prompt: str,
        artist_recommendations: List[str],
        target_features: Dict[str, Any],
        access_token: str,
        mood_analysis: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Get anchor candidates from top recommended artists, prioritizing those mentioned in prompt.

        Args:
            mood_prompt: User's mood prompt
            artist_recommendations: List of artist names from mood analysis
            target_features: Target audio features
            access_token: Spotify access token

        Returns:
            List of artist-based track candidate dictionaries
        """
        if not self.spotify_service or not artist_recommendations:
            return []

        candidates = []
        prompt_lower = mood_prompt.lower()

        # Prioritize artists mentioned in the prompt
        mentioned_artists = []
        other_artists = []

        for artist in artist_recommendations:
            if artist.lower() in prompt_lower:
                mentioned_artists.append(artist)
            else:
                other_artists.append(artist)

        # Process mentioned artists first (up to 3), then other top artists (up to 5 total)
        artists_to_process = mentioned_artists[:3] + other_artists[:5]

        # First, fetch all artist info
        artist_infos = []
        for artist_name in artists_to_process[:8]:  # Limit to 8 artists total
            try:
                logger.info(f"Searching for artist: {artist_name}")

                # Search for artist first to get the Spotify artist ID
                artists = await self.spotify_service.search_spotify_artists(
                    access_token=access_token,
                    query=artist_name,
                    limit=1
                )

                if not artists:
                    continue

                artist_info = artists[0]
                artist_id = artist_info.get('id')
                if artist_id:
                    artist_infos.append({
                        'info': artist_info,
                        'name': artist_name,
                        'is_mentioned': artist_name in mentioned_artists
                    })

            except Exception as e:
                logger.warning(f"Failed to search for artist '{artist_name}': {e}")
                continue

        # Batch validate artists with LLM
        if self.llm and mood_analysis and artist_infos:
            validated_artists = await self._batch_validate_artists(
                [a['info'] for a in artist_infos],
                mood_prompt,
                mood_analysis
            )
            validated_names = {a.get('name') for a in validated_artists}
            
            # Filter artist_infos to only validated ones
            artist_infos = [
                a for a in artist_infos 
                if a['info'].get('name') in validated_names
            ]
            logger.info(f"After batch validation: {len(artist_infos)} artists remaining")

        # Now fetch tracks for validated artists
        for artist_data in artist_infos:
            artist_info = artist_data['info']
            artist_name = artist_data['name']
            artist_id = artist_info.get('id')
            
            try:

                # Get top tracks for this artist
                tracks = await self.spotify_service.get_artist_top_tracks(
                    access_token=access_token,
                    artist_id=artist_id,
                    market='US'  # Could be made configurable
                )

                if not tracks:
                    continue

                # Take top 2 tracks per artist for mentioned artists, 1 for others
                limit_per_artist = 2 if artist_name in mentioned_artists else 1
                selected_tracks = tracks[:limit_per_artist]

                # Create candidates for each track
                for track in selected_tracks:
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
                            logger.warning(f"Failed to get features for artist track: {e}")

                    # Mark as artist-based anchor
                    is_mentioned_artist = artist_data['is_mentioned']
                    track['user_mentioned'] = is_mentioned_artist  # Mentioned artists get high priority
                    track['anchor_type'] = 'artist_mentioned' if is_mentioned_artist else 'artist_recommended'
                    track['protected'] = is_mentioned_artist  # Protect mentioned artist tracks

                    candidates.append({
                        'track': track,
                        'score': 0.9 if is_mentioned_artist else 0.8,  # High base score for artist tracks
                        'confidence': 0.95 if is_mentioned_artist else 0.9,
                        'features': features,
                        'artist': artist_name,
                        'source': 'artist_top_tracks',
                        'anchor_type': track['anchor_type'],
                        'user_mentioned': is_mentioned_artist,
                        'protected': is_mentioned_artist
                    })

            except Exception as e:
                logger.warning(f"Failed to get tracks for artist '{artist_name}': {e}")
                continue

        return candidates

    async def _batch_validate_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to batch validate artists for cultural/linguistic relevance.

        More efficient than individual validation and allows better comparative decisions.

        Args:
            artists: List of artist information from Spotify
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis context

        Returns:
            List of validated artists
        """
        if not self.llm or not artists:
            return artists  # No LLM available, allow all by default

        try:
            prompt = get_batch_artist_validation_prompt(artists, mood_prompt, mood_analysis)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            keep_indices = result.get('keep_artists', [])
            filtered_info = result.get('filtered_artists', [])
            
            # Log filtered artists
            for filter_info in filtered_info:
                name = filter_info.get('name', 'Unknown')
                reason = filter_info.get('reason', '')
                logger.info(f"LLM filtered artist '{name}': {reason}")
            
            # Return validated artists
            validated = []
            for idx in keep_indices:
                if 0 <= idx < len(artists):
                    validated.append(artists[idx])
            
            logger.info(f"Batch artist validation: kept {len(validated)}/{len(artists)} artists")
            return validated

        except Exception as e:
            logger.warning(f"Batch artist validation LLM call failed: {e}")
            return artists  # Default to allowing all if LLM fails

    async def _filter_tracks_by_relevance(
        self,
        tracks: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to filter out culturally/linguistically irrelevant tracks.

        Args:
            tracks: List of track candidates
            mood_prompt: User's mood prompt
            mood_analysis: Mood analysis context

        Returns:
            Filtered list of relevant tracks
        """
        if not self.llm or not tracks:
            return tracks

        try:
            # Format tracks for LLM
            tracks_for_llm = []
            for track in tracks:
                track_data = track.get('track', track)
                tracks_for_llm.append({
                    'name': track_data.get('name', ''),
                    'artists': track_data.get('artists', [])
                })

            prompt = get_batch_track_filter_prompt(tracks_for_llm, mood_prompt, mood_analysis)
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            result = LLMResponseParser.extract_json_from_response(response)

            relevant_indices = set(result.get('relevant_tracks', []))
            filtered_out = result.get('filtered_out', [])
            
            # Log filtered tracks
            for filter_info in filtered_out:
                track_idx = filter_info.get('track_index', -1)
                reason = filter_info.get('reason', '')
                if 0 <= track_idx < len(tracks_for_llm):
                    track_name = tracks_for_llm[track_idx].get('name', 'Unknown')
                    logger.info(f"LLM filtered track '{track_name}': {reason}")

            # Return only relevant tracks
            filtered_tracks = [
                tracks[i] for i in range(len(tracks))
                if i in relevant_indices
            ]

            logger.info(
                f"LLM track filtering: kept {len(filtered_tracks)}/{len(tracks)} tracks"
            )

            return filtered_tracks

        except Exception as e:
            logger.warning(f"Track filtering LLM call failed: {e}")
            return tracks  # Return all tracks if LLM fails

