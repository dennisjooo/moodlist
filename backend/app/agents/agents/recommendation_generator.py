"""Recommendation generator agent for creating mood-based track recommendations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus, TrackRecommendation
from ..tools.reccobeat_service import RecoBeatService
from ..tools.spotify_service import SpotifyService


logger = logging.getLogger(__name__)


class RecommendationGeneratorAgent(BaseAgent):
    """Agent for generating mood-based track recommendations."""

    def __init__(
        self,
        reccobeat_service: RecoBeatService,
        spotify_service: SpotifyService,
        max_recommendations: int = 30,
        diversity_factor: float = 0.7,
        verbose: bool = False
    ):
        """Initialize the recommendation generator agent.

        Args:
            reccobeat_service: Service for RecoBeat API operations
            spotify_service: Service for Spotify API operations
            max_recommendations: Maximum number of recommendations to generate
            diversity_factor: Factor for ensuring diversity in recommendations (0-1)
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="recommendation_generator",
            description="Generates sophisticated mood-based track recommendations using RecoBeat API",
            verbose=verbose
        )

        self.reccobeat_service = reccobeat_service
        self.spotify_service = spotify_service
        self.max_recommendations = max_recommendations
        self.diversity_factor = diversity_factor

    async def execute(self, state: AgentState) -> AgentState:
        """Execute recommendation generation.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with recommendations
        """
        try:
            logger.info(f"Generating recommendations for mood: {state.mood_prompt}")

            # Check if we have seed tracks
            if not state.seed_tracks:
                logger.warning("No seed tracks available for recommendations")
                # Try to generate recommendations without seeds as fallback
                recommendations = await self._generate_fallback_recommendations(state)
            else:
                # Generate recommendations using seeds and mood analysis
                recommendations = await self._generate_mood_based_recommendations(state)

            # Filter and rank recommendations
            filtered_recommendations = self._filter_and_rank_recommendations(
                recommendations,
                state.mood_analysis
            )

            # Ensure diversity in recommendations
            diverse_recommendations = self._ensure_diversity(filtered_recommendations)

            # Get playlist target to determine max recommendations
            playlist_target = state.metadata.get("playlist_target", {})
            max_recommendations = playlist_target.get("max_count", self.max_recommendations)
            
            # ENFORCE 95:5 ratio: separate artist vs RecoBeat tracks and cap each
            artist_recs = [r for r in diverse_recommendations if r.source == "artist_discovery"]
            reccobeat_recs = [r for r in diverse_recommendations if r.source == "reccobeat"]
            
            # Calculate strict caps based on 95:5 ratio
            max_artist = int(max_recommendations * 0.95)  # 95%
            max_reccobeat = max_recommendations - max_artist  # 5%
            
            # Take top tracks from each source up to their caps
            capped_artist = artist_recs[:max_artist]
            capped_reccobeat = reccobeat_recs[:max_reccobeat]
            
            logger.info(
                f"Enforcing 95:5 ratio: {len(capped_artist)} artist tracks (cap: {max_artist}), "
                f"{len(capped_reccobeat)} RecoBeat tracks (cap: {max_reccobeat})"
            )
            
            # Combine and sort by confidence
            final_recommendations = capped_artist + capped_reccobeat
            final_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

            # Update state with recommendations (with enhanced deduplication)
            seen_track_ids = set()
            seen_normalized_names = set()
            seen_spotify_uris = set()
            
            for rec in final_recommendations:
                # Check track ID
                if rec.track_id in seen_track_ids:
                    logger.debug(f"Skipping duplicate track ID: {rec.track_name} by {', '.join(rec.artists)}")
                    continue
                
                # Check normalized track name (case-insensitive, remove feat/featuring variations)
                normalized_name = rec.track_name.lower()
                # Remove common variations that create duplicates
                for variant in [" (radio edit)", " - radio edit", " (feat.", " (featuring ", " - feat.", " - featuring "]:
                    if variant in normalized_name:
                        normalized_name = normalized_name.split(variant)[0]
                normalized_name = normalized_name.strip()
                
                if normalized_name in seen_normalized_names:
                    logger.debug(f"Skipping duplicate track name: {rec.track_name} by {', '.join(rec.artists)}")
                    continue
                
                # Check Spotify URI
                if rec.spotify_uri and rec.spotify_uri in seen_spotify_uris:
                    logger.debug(f"Skipping duplicate Spotify URI: {rec.track_name} by {', '.join(rec.artists)}")
                    continue
                
                # No duplicates found, add the track
                state.add_recommendation(rec)
                seen_track_ids.add(rec.track_id)
                seen_normalized_names.add(normalized_name)
                if rec.spotify_uri:
                    seen_spotify_uris.add(rec.spotify_uri)

            state.current_step = "recommendations_generated"
            state.status = RecommendationStatus.GENERATING_RECOMMENDATIONS

            # Store metadata
            state.metadata["total_recommendations_generated"] = len(diverse_recommendations)
            state.metadata["final_recommendation_count"] = len(state.recommendations)
            state.metadata["recommendation_strategy"] = "mood_based_with_seeds"

            logger.info(f"Generated {len(state.recommendations)} final recommendations")

        except Exception as e:
            logger.error(f"Error in recommendation generation: {str(e)}", exc_info=True)
            state.set_error(f"Recommendation generation failed: {str(e)}")

        return state

    async def _generate_mood_based_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations based on mood analysis, seeds, and discovered artists.
        
        Target ratio: 95:5 (95% from artist discovery, 5% from seed-based recommendations).
        Artist discovery is overwhelmingly prioritized as RecoBeat recommendations tend to be lower quality.
        
        RecoBeat API calls use ONLY seeds, negative_seeds, and size parameters.
        Audio feature parameters are NOT used as they cause RecoBeat to return irrelevant tracks.

        Args:
            state: Current agent state

        Returns:
            List of raw recommendations (mostly from artist discovery)
        """
        all_recommendations = []
        
        # Get target to calculate desired split
        playlist_target = state.metadata.get("playlist_target", {})
        target_count = playlist_target.get("target_count", 20)
        
        # Calculate target split: 95:5 ratio (95% artists, 5% seeds)
        target_artist_recs = int(target_count * 0.95)  # 95% from artists
        target_seed_recs = target_count - target_artist_recs  # 5% from seeds
        
        # Store targets in state for use by generation methods
        state.metadata["_temp_seed_target"] = target_seed_recs
        state.metadata["_temp_artist_target"] = target_artist_recs
        
        logger.info(
            f"Target generation split (95:5 ratio): {target_artist_recs} from artists, "
            f"{target_seed_recs} from seeds (total: {target_count})"
        )
        
        # Generate from discovered artists FIRST (aiming for 2/3 of target - higher priority)
        artist_recommendations = await self._generate_from_discovered_artists(state)
        all_recommendations.extend(artist_recommendations)
        
        # Generate from seed tracks (aiming for 1/3 of target - supplement only)
        seed_recommendations = await self._generate_from_seeds(state)
        all_recommendations.extend(seed_recommendations)
        
        # Clean up temp metadata
        state.metadata.pop("_temp_seed_target", None)
        state.metadata.pop("_temp_artist_target", None)
        
        logger.info(
            f"Generated {len(all_recommendations)} total recommendations "
            f"({len(artist_recommendations)} from artists [{target_artist_recs} target], "
            f"{len(seed_recommendations)} from seeds [{target_seed_recs} target])"
        )
        
        return all_recommendations

    async def _generate_from_seeds(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from seed tracks.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from seed tracks
        """
        all_recommendations = []
        
        # Deduplicate seeds before processing
        unique_seeds = list(dict.fromkeys(state.seed_tracks))  # Preserves order
        if len(unique_seeds) < len(state.seed_tracks):
            logger.info(f"Deduplicated seeds: {len(state.seed_tracks)} -> {len(unique_seeds)}")
        
        # Split seeds into smaller chunks for multiple API calls
        seed_chunks = self._chunk_seeds(unique_seeds, chunk_size=3)
        
        # Get seed target (5% of total playlist target - very minimal supplementary)
        target_seed_recs = state.metadata.get("_temp_seed_target", 1)  # Default ~5% of 20
        
        # Request more per chunk to account for filtering (aim for 2x target due to low count)
        # This gives us room for filtering while targeting the right amount
        per_chunk_size = min(10, max(int((target_seed_recs * 2) // len(seed_chunks)) + 2, 3))
        
        # Prepare minimal RecoBeat params (NO audio features - they cause issues)
        reccobeat_params = {}
        
        # Add negative seeds if available (limit to 5 as per RecoBeat API)
        if state.negative_seeds:
            reccobeat_params["negative_seeds"] = state.negative_seeds[:5]
            logger.info(f"Using {len(reccobeat_params['negative_seeds'])} negative seeds to avoid similar tracks")
        
        for chunk in seed_chunks:
            try:
                # Get recommendations for this seed chunk
                # ONLY use seeds, negative_seeds, and size - NO audio feature params
                chunk_recommendations = await self.reccobeat_service.get_track_recommendations(
                    seeds=chunk,
                    size=per_chunk_size,
                    **reccobeat_params
                )

                # Convert to TrackRecommendation objects
                for rec_data in chunk_recommendations:
                    try:
                        track_id = rec_data.get("track_id", "")
                        if not track_id:
                            logger.warning("Skipping recommendation without track ID")
                            continue

                        # Get complete audio features for this track
                        complete_audio_features = await self._get_complete_audio_features(
                            track_id, rec_data.get("audio_features")
                        )

                        # Use confidence score from RecoBeat if available, otherwise calculate
                        confidence = rec_data.get("confidence_score")
                        if confidence is None:
                            confidence = self._calculate_confidence_score(rec_data, state)

                        recommendation = TrackRecommendation(
                            track_id=track_id,
                            track_name=rec_data.get("track_name", "Unknown Track"),
                            artists=rec_data.get("artists", ["Unknown Artist"]),
                            spotify_uri=rec_data.get("spotify_uri"),
                            confidence_score=confidence,
                            audio_features=complete_audio_features,
                            reasoning=rec_data.get("reasoning", f"Mood-based recommendation using seeds: {', '.join(chunk)}"),
                            source=rec_data.get("source", "reccobeat")
                        )
                        all_recommendations.append(recommendation)

                    except Exception as e:
                        logger.warning(f"Failed to create recommendation object: {e}")
                        continue

                # Add some delay between API calls to respect rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating recommendations for seed chunk {chunk}: {e}")
                continue

        logger.info(f"Generated {len(all_recommendations)} raw recommendations from {len(seed_chunks)} seed chunks")

        # Apply validation pass to filter out irrelevant tracks
        validated_recommendations = []
        for rec in all_recommendations:
            is_valid, reason = self._validate_track_relevance(
                rec.track_name, rec.artists, state.mood_analysis
            )
            if is_valid:
                validated_recommendations.append(rec)
            else:
                logger.info(f"Filtered out invalid track from seeds: {rec.track_name} by {', '.join(rec.artists)} - {reason}")
        
        logger.info(f"Validation pass: {len(all_recommendations)} -> {len(validated_recommendations)} tracks (filtered {len(all_recommendations) - len(validated_recommendations)})")

        return [rec.dict() for rec in validated_recommendations]

    async def _get_complete_audio_features(
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

    def _validate_track_relevance(
        self,
        track_name: str,
        artists: List[str],
        mood_analysis: Optional[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """Validate if a track is relevant to the mood before accepting.
        
        Filters out obvious mismatches (wrong language, genre, etc.)
        
        Args:
            track_name: Track name to validate
            artists: List of artist names
            mood_analysis: Mood analysis with artist recommendations and keywords
            
        Returns:
            (is_valid, reason) - True if track is relevant, False with reason if not
        """
        if not mood_analysis:
            return (True, "No mood analysis available")
        
        # Get mood context
        artist_recommendations = mood_analysis.get("artist_recommendations", [])
        genre_keywords = mood_analysis.get("genre_keywords", [])
        search_keywords = mood_analysis.get("search_keywords", [])
        mood_prompt = mood_analysis.get("mood_interpretation", "")
        
        # Normalize for comparison
        track_lower = track_name.lower()
        artists_lower = [a.lower() for a in artists]
        artist_recs_lower = [a.lower() for a in artist_recommendations]
        
        # Check 1: If artist is in recommended artists, always accept
        for artist in artists_lower:
            if any(rec_artist in artist or artist in rec_artist for rec_artist in artist_recs_lower):
                return (True, "Artist matches mood recommendations")
        
        # Check 2: Language/region mismatch detection
        # Detect obvious language mismatches by checking for non-Latin characters or language-specific names
        language_indicators = {
            "spanish": ["el ", "la ", "los ", "las ", "mi ", "tu ", "de ", "con ", "por ", "para "],
            "korean": ["\u3131", "\u314f", "\uac00", "\ud7a3"],  # Hangul character ranges
            "japanese": ["\u3040", "\u309f", "\u30a0", "\u30ff"],  # Hiragana/Katakana
            "chinese": ["\u4e00", "\u9fff"],  # Common CJK
            "portuguese": ["meu ", "minha ", "você ", "está ", "muito ", "bem "],
            "german": ["der ", "die ", "das ", "ich ", "du ", "und ", "mit "],
            "french": ["le ", "la ", "les ", "de ", "je ", "tu ", "avec ", "pour "]
        }
        
        # Combine all keywords for mood language detection
        all_keywords = genre_keywords + search_keywords
        mood_language = None
        
        # Detect mood language from keywords
        for keyword in all_keywords:
            keyword_lower = keyword.lower()
            if any(lang_word in keyword_lower for lang_word in ["french", "français"]):
                mood_language = "french"
                break
            elif any(lang_word in keyword_lower for lang_word in ["spanish", "latin", "latino"]):
                mood_language = "spanish"
                break
            elif any(lang_word in keyword_lower for lang_word in ["korean", "k-pop", "kpop"]):
                mood_language = "korean"
                break
            elif any(lang_word in keyword_lower for lang_word in ["japanese", "j-pop", "jpop", "city pop"]):
                mood_language = "japanese"
                break
            elif any(lang_word in keyword_lower for lang_word in ["portuguese", "brazilian", "bossa"]):
                mood_language = "portuguese"
                break
        
        # If we detected a specific mood language, check if track matches
        if mood_language:
            track_and_artists = track_lower + " " + " ".join(artists_lower)
            
            for lang, indicators in language_indicators.items():
                if lang == mood_language:
                    continue  # Skip checking against the mood's own language
                
                # Check if track has indicators of a different language
                for indicator in indicators:
                    if isinstance(indicator, str):
                        if indicator in track_and_artists:
                            return (False, f"Language mismatch: track appears to be {lang}, mood is {mood_language}")
                    else:
                        # Unicode range check for CJK languages
                        for char in track_name:
                            if indicator <= char <= indicators[indicators.index(indicator) + 1]:
                                return (False, f"Language mismatch: track appears to be {lang}, mood is {mood_language}")
        
        # Check 3: Genre/style keyword overlap
        # Extract potential genre words from track/artist names
        genre_terms = ["funk", "disco", "house", "techno", "jazz", "rock", "pop", "indie", 
                       "electronic", "hip hop", "rap", "soul", "blues", "metal", "punk",
                       "reggae", "country", "folk", "classical", "ambient", "trap"]
        
        track_genres = []
        mood_genres = []
        
        # Find genres in track/artist
        for term in genre_terms:
            if term in track_and_artists:
                track_genres.append(term)
        
        # Find genres in mood keywords
        for keyword in all_keywords:
            keyword_lower = keyword.lower()
            for term in genre_terms:
                if term in keyword_lower:
                    mood_genres.append(term)
        
        # If both have genre indicators and they don't overlap at all, flag it
        if track_genres and mood_genres:
            # Check for conflicting genres (e.g., "hip hop" for "indie rock")
            conflicting_pairs = [
                (["classical", "jazz", "blues"], ["metal", "punk", "trap"]),
                (["folk", "country", "indie"], ["electronic", "techno", "house"]),
                (["hip hop", "rap", "trap"], ["rock", "indie", "folk"])
            ]
            
            for group1, group2 in conflicting_pairs:
                has_group1 = any(g in track_genres for g in group1)
                has_group2 = any(g in mood_genres for g in group2)
                if has_group1 and has_group2:
                    return (False, f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}")
                
                # Check reverse
                has_group1_mood = any(g in mood_genres for g in group1)
                has_group2_track = any(g in track_genres for g in group2)
                if has_group1_mood and has_group2_track:
                    return (False, f"Genre conflict: track appears to be {track_genres}, mood is {mood_genres}")
        
        # If we got here, no obvious red flags
        return (True, "No obvious mismatches detected")

    async def _generate_fallback_recommendations(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when no seeds are available.

        Args:
            state: Current agent state

        Returns:
            List of fallback recommendations
        """
        logger.info("Generating fallback recommendations without seeds")

        # Use mood-based search with artist keywords
        # Support both old format (search_keywords) and new format (keywords)
        if state.mood_analysis:
            keywords = state.mood_analysis.get("keywords") or state.mood_analysis.get("search_keywords")
            
            if keywords:
                # Use top 3 keywords
                keywords_to_use = keywords[:3] if isinstance(keywords, list) else [keywords]

                # Search for artists matching mood keywords
                matching_artists = await self.reccobeat_service.search_artists_by_mood(
                    keywords_to_use,
                    limit=5
                )

                if matching_artists:
                    # Use found artists as seeds for recommendations
                    artist_ids = [artist["id"] for artist in matching_artists if artist.get("id")]

                    if artist_ids:
                        # Deduplicate artist IDs
                        unique_artist_ids = list(dict.fromkeys(artist_ids[:3]))
                        fallback_recommendations = await self.reccobeat_service.get_track_recommendations(
                            seeds=unique_artist_ids,
                            size=20
                            # NO audio feature params - keep it simple
                        )

                        logger.info(f"Generated {len(fallback_recommendations)} fallback recommendations using {len(artist_ids)} artists")
                        return fallback_recommendations

        # If all else fails, return empty list
        logger.warning("Could not generate fallback recommendations")
        return []

    def _chunk_seeds(self, seeds: List[str], chunk_size: int = 3) -> List[List[str]]:
        """Split seeds into smaller chunks for API calls.

        Args:
            seeds: List of seed track IDs
            chunk_size: Size of each chunk

        Returns:
            List of seed chunks
        """
        chunks = []
        for i in range(0, len(seeds), chunk_size):
            chunk = seeds[i:i + chunk_size]
            if len(chunk) > 0:  # Only add non-empty chunks
                chunks.append(chunk)
        return chunks

    def _extract_mood_features(self, state: AgentState) -> Dict[str, Any]:
        """Extract features for RecoBeat API.
        
        DEPRECATED: We now only use seeds and negative_seeds, no audio features.
        Audio feature parameters cause RecoBeat to return irrelevant tracks.

        Args:
            state: Current agent state with mood analysis and target features

        Returns:
            Empty dict (audio features no longer used)
        """
        logger.info("Audio features extraction skipped - using seed-based recommendations only")
        return {}

    def _calculate_confidence_score(
        self,
        recommendation_data: Dict[str, Any],
        state: AgentState
    ) -> float:
        """Calculate confidence score for a recommendation.

        Args:
            recommendation_data: Raw recommendation data
            state: Current agent state

        Returns:
            Confidence score (0-1)
        """
        # Check if RecoBeat provided a score/rating
        if "score" in recommendation_data:
            # RecoBeat returns scores typically 0-100, normalize to 0-1
            return min(recommendation_data["score"] / 100.0, 1.0)
        
        if "rating" in recommendation_data:
            # If rating is already 0-1, use it directly
            rating = recommendation_data["rating"]
            return rating if rating <= 1.0 else rating / 100.0
        
        if "confidence" in recommendation_data:
            return min(recommendation_data["confidence"], 1.0)

        # Fallback calculation using popularity and mood match
        base_score = 0.6  # Higher base score
        
        # Factor in track popularity if available
        popularity = recommendation_data.get("popularity", 0)
        if popularity > 0:
            # Scale popularity contribution
            popularity_factor = min(popularity / 100.0, 1.0)
            base_score += (0.15 * popularity_factor)
        
        # Factor in audio features match with mood using complete features
        target_features = state.metadata.get("target_features", {})
        if target_features and recommendation_data.get("audio_features"):
            mood_match_score = self._calculate_mood_match(
                recommendation_data["audio_features"],
                target_features
            )
            base_score += (0.4 * mood_match_score)  # Increased weight for mood matching
            
            # Apply penalties for critical feature violations
            audio_features = recommendation_data["audio_features"]
            penalty = 0.0
            
            # Penalize high speechiness if target is low
            if "speechiness" in target_features and "speechiness" in audio_features:
                target_speech = target_features["speechiness"]
                actual_speech = audio_features["speechiness"]
                if target_speech < 0.2 and actual_speech > 0.3:
                    penalty += 0.15 * (actual_speech - 0.3)
            
            # Penalize high liveness if target is low
            if "liveness" in target_features and "liveness" in audio_features:
                target_live = target_features["liveness"]
                actual_live = audio_features["liveness"]
                if target_live < 0.3 and actual_live > 0.5:
                    penalty += 0.1 * (actual_live - 0.5)
            
            base_score -= penalty
            
        elif target_features:
            # Boost for having target features even without audio features
            base_score += 0.1
        
        # Apply source penalty - RecoBeat has circular dependency bias
        # (recommendations are generated using target features, so they score high but may be irrelevant)
        if recommendation_data.get("source") == "reccobeat":
            base_score *= 0.85  # 15% penalty for RecoBeat bias

        return min(max(base_score, 0.0), 1.0)
    
    def _calculate_mood_match(
        self,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well audio features match target mood features.
        
        Args:
            audio_features: Track audio features
            target_features: Target mood features
            
        Returns:
            Match score (0-1)
        """
        if not audio_features or not target_features:
            return 0.5
        
        # Compare key features
        feature_keys = ["energy", "valence", "danceability", "acousticness"]
        matches = 0
        total_features = 0
        
        for key in feature_keys:
            if key in audio_features and key in target_features:
                track_value = audio_features[key]
                target_value = target_features[key]
                
                # Handle range values as string (e.g., "0.8-1.0")
                if isinstance(target_value, str):
                    try:
                        if '-' in target_value:
                            parts = target_value.split('-')
                            if len(parts) == 2:
                                min_val = float(parts[0])
                                max_val = float(parts[1])
                                target_mid = (min_val + max_val) / 2
                                # Calculate similarity (closer = better)
                                similarity = 1.0 - abs(track_value - target_mid)
                                matches += similarity
                            else:
                                # Single value as string
                                target_num = float(target_value)
                                similarity = 1.0 - abs(track_value - target_num)
                                matches += similarity
                        else:
                            # Single value as string
                            target_num = float(target_value)
                            similarity = 1.0 - abs(track_value - target_num)
                            matches += similarity
                        total_features += 1
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse target value '{target_value}' for {key}: {e}")
                        continue
                # Handle range values as list (e.g., [0.8, 1.0])
                elif isinstance(target_value, list) and len(target_value) == 2:
                    target_mid = sum(target_value) / 2
                    # Calculate similarity (closer = better)
                    similarity = 1.0 - abs(track_value - target_mid)
                    matches += similarity
                    total_features += 1
                # Handle numeric values
                elif isinstance(target_value, (int, float)):
                    similarity = 1.0 - abs(track_value - target_value)
                    matches += similarity
                    total_features += 1
        
        return matches / total_features if total_features > 0 else 0.5

    def _filter_and_rank_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        mood_analysis: Optional[Dict[str, Any]] = None
    ) -> List[TrackRecommendation]:
        """Filter and rank recommendations based on mood analysis.

        Args:
            recommendations: Raw recommendations
            mood_analysis: Mood analysis results

        Returns:
            Filtered and ranked TrackRecommendation objects
        """
        if not recommendations:
            return []

        # Convert to TrackRecommendation objects
        rec_objects = []
        for rec_data in recommendations:
            try:
                # Handle both 'track_id' and 'id' fields for compatibility
                track_id = rec_data.get("track_id") or rec_data.get("id", "")
                if not track_id:
                    logger.warning("Skipping recommendation without track ID")
                    continue
                
                rec_obj = TrackRecommendation(
                    track_id=track_id,
                    track_name=rec_data.get("track_name", "Unknown Track"),
                    artists=rec_data.get("artists", ["Unknown Artist"]),
                    spotify_uri=rec_data.get("spotify_uri"),
                    confidence_score=rec_data.get("confidence_score", 0.5),
                    audio_features=rec_data.get("audio_features"),
                    reasoning=rec_data.get("reasoning", "Mood-based recommendation"),
                    source=rec_data.get("source", "reccobeat")
                )
                rec_objects.append(rec_obj)

            except Exception as e:
                logger.warning(f"Failed to create recommendation object: {e}")
                continue

        # Sort by confidence score before filtering
        rec_objects.sort(key=lambda x: x.confidence_score, reverse=True)

        # Apply mood-based filtering if available
        if mood_analysis and mood_analysis.get("target_features"):
            rec_objects = self._apply_mood_filtering(rec_objects, mood_analysis)

        return rec_objects

    def _apply_mood_filtering(
        self,
        recommendations: List[TrackRecommendation],
        mood_analysis: Dict[str, Any]
    ) -> List[TrackRecommendation]:
        """Apply mood-based filtering to recommendations with strict tolerance thresholds.

        Args:
            recommendations: List of recommendations to filter
            mood_analysis: Mood analysis results

        Returns:
            Filtered recommendations that meet mood constraints
        """
        if not mood_analysis.get("target_features"):
            return recommendations

        target_features = mood_analysis["target_features"]
        filtered_recommendations = []
        
        # Define tolerance thresholds for different feature types
        tolerance_thresholds = {
            # Critical features - tighter control
            "speechiness": 0.20,  # Reduced from 0.25
            "instrumentalness": 0.20,  # Reduced from 0.25
            # Important features - tighten slightly
            "energy": 0.25,  # Reduced from 0.3
            "valence": 0.25,  # Reduced from 0.3
            "danceability": 0.25,  # Reduced from 0.3
            # Flexible features - keep reasonable
            "tempo": 40.0,
            "loudness": 6.0,
            "acousticness": 0.35,  # Reduced from 0.4
            "liveness": 0.35,  # Reduced from 0.4
            "mode": None,  # Binary, no tolerance
            "key": None,  # Discrete, no tolerance
            "popularity": 25  # Reduced from 30
        }

        for rec in recommendations:
            if not rec.audio_features:
                # Keep tracks without audio features (will have lower confidence anyway)
                filtered_recommendations.append(rec)
                continue
            
            should_filter = False
            violations = []
            
            # Check each target feature against the track's audio features
            for feature_name, target_value in target_features.items():
                if feature_name not in rec.audio_features:
                    continue
                
                actual_value = rec.audio_features[feature_name]
                tolerance = tolerance_thresholds.get(feature_name)
                
                # Convert target_value to single value if it's a range
                if isinstance(target_value, list) and len(target_value) == 2:
                    target_single = sum(target_value) / 2  # Use midpoint
                elif isinstance(target_value, (int, float)):
                    target_single = float(target_value)
                else:
                    continue  # Skip if we can't parse the target value
                
                if tolerance is None:
                    # Binary or discrete features - exact or close match required
                    if feature_name in ["mode", "key"]:
                        continue  # Skip strict filtering for mode/key
                else:
                    # Check if actual value is within tolerance
                    difference = abs(actual_value - target_single)
                    if difference > tolerance:
                        violations.append(f"{feature_name}: target={target_single:.2f}, actual={actual_value:.2f}, diff={difference:.2f}")
                        
                        # Critical features cause immediate filtering if moderately out of range
                        if feature_name in ["speechiness", "instrumentalness"]:
                            # Filter if difference is more than 1.5x tolerance (was 2x)
                            if difference > tolerance * 1.5:
                                should_filter = True
                        elif feature_name in ["energy", "valence"]:
                            # Filter if difference is more than 1.8x tolerance
                            if difference > tolerance * 1.8:
                                should_filter = True
            
            if should_filter:
                logger.debug(f"Filtered out '{rec.track_name}' by {', '.join(rec.artists)} due to violations: {'; '.join(violations)}")
            else:
                if violations:
                    logger.debug(f"Keeping '{rec.track_name}' despite minor violations: {'; '.join(violations)}")
                filtered_recommendations.append(rec)

        logger.info(f"Mood filtering: {len(recommendations)} -> {len(filtered_recommendations)} tracks")
        return filtered_recommendations

    def _ensure_diversity(
        self,
        recommendations: List[TrackRecommendation]
    ) -> List[TrackRecommendation]:
        """Ensure diversity in recommendations to avoid repetition.

        Args:
            recommendations: List of recommendations to diversify

        Returns:
            Diversified recommendations
        """
        if not recommendations:
            return recommendations

        # Simple diversity approach: reduce weight of artists that appear multiple times
        artist_counts = {}
        diversified_recommendations = []

        for rec in recommendations:
            # Count artist occurrences
            for artist in rec.artists:
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

            # Reduce confidence score for artists that appear multiple times
            diversity_penalty = 0
            for artist in rec.artists:
                if artist_counts[artist] > 1:
                    diversity_penalty += 0.1 * (artist_counts[artist] - 1)

            # Apply diversity penalty
            adjusted_confidence = rec.confidence_score - diversity_penalty
            adjusted_confidence = max(adjusted_confidence, 0.1)  # Minimum confidence

            # Create new recommendation with adjusted confidence
            diversified_rec = TrackRecommendation(
                track_id=rec.track_id,
                track_name=rec.track_name,
                artists=rec.artists,
                spotify_uri=rec.spotify_uri,
                confidence_score=adjusted_confidence,
                audio_features=rec.audio_features,
                reasoning=rec.reasoning,  # Keep original reasoning, adjustment is in confidence score
                source=rec.source
            )

            diversified_recommendations.append(diversified_rec)

        # Re-sort by adjusted confidence
        diversified_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

        return diversified_recommendations

    async def _generate_from_discovered_artists(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate recommendations from mood-matched artists.

        Args:
            state: Current agent state

        Returns:
            List of recommendations from discovered artists
        """
        all_recommendations = []
        
        # Get mood-matched artists from state metadata
        mood_matched_artists = state.metadata.get("mood_matched_artists", [])
        
        if not mood_matched_artists:
            logger.info("No mood-matched artists available for recommendations")
            return all_recommendations
        
        logger.info(f"Generating recommendations from {len(mood_matched_artists)} discovered artists")
        
        # Get target features for filtering
        target_features = state.metadata.get("target_features", {})
        
        # Get artist target (95% of total playlist target - DOMINANT source, 95:5 ratio)
        target_artist_recs = state.metadata.get("_temp_artist_target", 19)  # Default 95% of 20
        
        # Track successful artists
        successful_artists = 0
        
        # Get access token for Spotify API
        access_token = state.metadata.get("spotify_access_token")
        if not access_token:
            logger.warning("No Spotify access token available for artist top tracks")
            return all_recommendations
        
        # MAXIMIZE DIVERSITY: Use MORE artists with FEWER tracks each
        # This gives broader representation of the mood/genre
        # For a target of ~19 tracks: 10 artists × 2-3 tracks = 20-30 tracks before filtering
        artist_count = min(len(mood_matched_artists), 20)  # Use up to 20 artists for maximum variety
        tracks_per_artist = max(2, min(int((target_artist_recs * 1.5) // artist_count) + 1, 3))
        
        logger.info(
            f"MAXIMIZING DIVERSITY: Fetching {tracks_per_artist} tracks from up to {artist_count} artists "
            f"to reach artist target of {target_artist_recs} tracks (95:5 ratio)"
        )
        
        # Fetch tracks from each artist (use up to 20 artists for maximum coverage and variety)
        for artist_id in mood_matched_artists[:20]:  # Increased to 20 artists for max diversity
            try:
                # Get top tracks from Spotify (more reliable than RecoBeat)
                artist_tracks = await self.spotify_service.get_artist_top_tracks(
                    access_token=access_token,
                    artist_id=artist_id,
                    market="US"
                )
                
                if not artist_tracks:
                    logger.debug(f"No tracks found for artist {artist_id}")
                    continue
                
                successful_artists += 1
                
                # Score and filter tracks by audio features (dynamic count)
                for track in artist_tracks[:tracks_per_artist]:
                    try:
                        # Spotify returns tracks with 'id' key
                        track_id = track.get("id")
                        if not track_id:
                            logger.debug(f"Skipping track without ID: {track}")
                            continue
                        
                        # Get audio features
                        audio_features = await self._get_complete_audio_features(track_id)
                        
                        # Score track against mood (RELAXED for artist tracks)
                        if target_features and audio_features:
                            cohesion_score = self._calculate_track_cohesion(
                                audio_features, target_features
                            )
                            
                            # Relaxed threshold for artist tracks (0.4 vs 0.6 for RecoBeat)
                            # Artist tracks are from curated top tracks, less strict filtering needed
                            if cohesion_score < 0.4:
                                logger.debug(f"Skipping artist track {track_id} (cohesion: {cohesion_score:.2f} - relaxed threshold)")
                                continue
                        else:
                            cohesion_score = 0.75  # Higher default for artist tracks without features
                        
                        # Create recommendation (extract artist names from Spotify format)
                        artist_names = [artist.get("name", "Unknown") for artist in track.get("artists", [])]
                        
                        recommendation = TrackRecommendation(
                            track_id=track_id,
                            track_name=track.get("name", "Unknown Track"),
                            artists=artist_names if artist_names else ["Unknown Artist"],
                            spotify_uri=track.get("spotify_uri"),
                            confidence_score=cohesion_score,
                            audio_features=audio_features,
                            reasoning=f"From mood-matched artist (cohesion: {cohesion_score:.2f})",
                            source="artist_discovery"
                        )
                        
                        all_recommendations.append(recommendation)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process artist track: {e}")
                        continue
                
                # Small delay between artists
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error getting tracks for artist {artist_id}: {e}")
                continue
        
        logger.info(
            f"Generated {len(all_recommendations)} recommendations from {successful_artists}/{min(len(mood_matched_artists), 20)} artists "
            f"(maximized diversity by spreading across more artists)"
        )
        
        return [rec.dict() for rec in all_recommendations]

    def _calculate_track_cohesion(
        self,
        audio_features: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> float:
        """Calculate how well a track's audio features match target mood features.

        Args:
            audio_features: Track's audio features
            target_features: Target mood features

        Returns:
            Cohesion score (0-1)
        """
        if not audio_features or not target_features:
            return 0.5
        
        scores = []
        
        # Define tolerance thresholds
        tolerance_thresholds = {
            "energy": 0.3,
            "valence": 0.3,
            "danceability": 0.3,
            "acousticness": 0.4,
            "instrumentalness": 0.25,
            "speechiness": 0.25,
            "tempo": 40.0,
            "loudness": 6.0,
            "liveness": 0.4,
            "popularity": 30
        }
        
        for feature_name, target_value in target_features.items():
            if feature_name not in audio_features:
                continue
            
            actual_value = audio_features[feature_name]
            tolerance = tolerance_thresholds.get(feature_name)
            
            if tolerance is None:
                continue
            
            # Convert target value to single number if it's a range
            if isinstance(target_value, list) and len(target_value) == 2:
                target_single = sum(target_value) / 2
            elif isinstance(target_value, (int, float)):
                target_single = float(target_value)
            else:
                continue
            
            # Calculate difference and score
            difference = abs(actual_value - target_single)
            match_score = max(0.0, 1.0 - (difference / tolerance))
            scores.append(match_score)
        
        # Return average match score
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5