"""Track processing utilities for anchor track selection."""

import structlog
from typing import Any, Dict, List, Optional

logger = structlog.get_logger(__name__)


class TrackProcessor:
    """Handles track processing, scoring, and feature matching."""

    def __init__(self, reccobeat_service=None):
        """Initialize the track processor.

        Args:
            reccobeat_service: Service for getting audio features
        """
        self.reccobeat_service = reccobeat_service

    async def get_track_features_batch(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get audio features for multiple tracks in batch.

        Args:
            track_ids: List of Spotify track IDs

        Returns:
            Dictionary mapping track IDs to their audio features
        """
        if not self.reccobeat_service or not track_ids:
            return {}

        try:
            return await self.reccobeat_service.get_tracks_audio_features(track_ids)
        except Exception as e:
            logger.warning(f"Failed to get batch audio features: {e}")
            return {}

    def calculate_feature_match(self, track_features: Dict[str, Any], target_features: Dict[str, Any]) -> float:
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

    def detect_track_script(self, track_name: str, artist_names: List[str]) -> str:
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

    def should_apply_language_penalty(
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

    def check_temporal_match(
        self,
        track: Dict[str, Any],
        temporal_context: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Check if a track matches the temporal context requirements.

        Args:
            track: Track dictionary from Spotify (should have album.release_date)
            temporal_context: Temporal context from mood analysis

        Returns:
            Tuple of (is_match, reason) - (True, None) if matches or no constraint,
            (False, reason) if violates temporal requirement
        """
        # If no temporal context or not temporal, allow all tracks
        if not temporal_context or not temporal_context.get('is_temporal'):
            return (True, None)

        # Extract year range
        year_range = temporal_context.get('year_range')
        if not year_range or len(year_range) != 2:
            return (True, None)

        min_year, max_year = year_range

        # Get release date from track
        album = track.get('album', {})
        release_date = album.get('release_date', '')

        if not release_date:
            # No release date - allow it (might be incomplete data)
            logger.debug(f"Track '{track.get('name')}' has no release_date, allowing")
            return (True, None)

        # Parse year from release_date (formats: YYYY, YYYY-MM-DD, YYYY-MM)
        try:
            release_year = int(release_date.split('-')[0])
        except (ValueError, IndexError):
            logger.debug(f"Could not parse release_date '{release_date}', allowing")
            return (True, None)

        # Check if within range
        if min_year <= release_year <= max_year:
            return (True, None)
        else:
            decade = temporal_context.get('decade', f'{min_year}-{max_year}')
            reason = (
                f"Released in {release_year}, outside {decade} requirement "
                f"({min_year}-{max_year})"
            )
            return (False, reason)

    def create_candidate_from_track(
        self,
        track: Dict[str, Any],
        target_features: Dict[str, Any],
        genre: str,
        mood_prompt: str,
        genre_keywords: List[str],
        features: Optional[Dict[str, Any]] = None,
        source: str = "genre_search",
        temporal_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create an anchor candidate from a track with scoring.

        Args:
            track: Track dictionary from Spotify
            target_features: Target audio features
            genre: Genre name for metadata
            mood_prompt: Original user prompt
            genre_keywords: All genre keywords
            features: Pre-fetched audio features
            source: Source of the track
            temporal_context: Temporal context from mood analysis (optional)

        Returns:
            Anchor candidate dictionary, or None if track should be filtered
        """
        track_id = track.get('id')
        if not track_id:
            return None

        # CRITICAL: Check temporal match first - filter out before any processing
        is_temporal_match, temporal_reason = self.check_temporal_match(track, temporal_context)
        if not is_temporal_match:
            artist_names = [a.get('name', '') for a in track.get('artists', [])]
            logger.info(
                f"✗ Filtered '{track.get('name')}' by {', '.join(artist_names)}: {temporal_reason}"
            )
            return None

        # Get features if not provided
        if features is None:
            features = {}
            if self.reccobeat_service:
                try:
                    features_map = self.get_track_features_batch([track_id])
                    features = features_map.get(track_id, {})
                    if features:
                        track['audio_features'] = features
                except Exception as e:
                    logger.warning(f"Failed to get features for track {track_id}: {e}")

        # Calculate base score
        if features:
            feature_score = self.calculate_feature_match(features, target_features)
        else:
            feature_score = 0.6

        # Weight popularity for better mainstream alignment
        popularity = track.get('popularity', 50) / 100.0  # Normalize to 0-1
        final_score = feature_score * 0.7 + popularity * 0.3

        # Context-aware language filtering
        artist_names = [a.get('name', '') for a in track.get('artists', [])]
        track_script = self.detect_track_script(track.get('name', ''), artist_names)

        if self.should_apply_language_penalty(track_script, mood_prompt, genre_keywords):
            final_score *= 0.5
            logger.debug(
                f"Applied language mismatch penalty to '{track.get('name')}' "
                f"by {', '.join(artist_names)} (script: {track_script})"
            )

        # Mark genre-based anchor metadata (can be filtered if poor fit)
        track['user_mentioned'] = False
        track['anchor_type'] = 'genre'
        track['protected'] = False  # Genre anchors can be filtered

        return {
            'track': track,
            'score': final_score,
            'confidence': 0.85,  # Standard confidence for genre anchors
            'features': features,
            'genre': genre,
            'anchor_type': 'genre',
            'user_mentioned': False,
            'protected': False,
            'source': source
        }