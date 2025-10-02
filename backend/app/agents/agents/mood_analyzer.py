"""Mood analyzer agent for understanding user mood prompts."""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models.base import BaseLanguageModel

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus


logger = logging.getLogger(__name__)


class MoodAnalyzerAgent(BaseAgent):
    """Agent for analyzing and understanding user mood prompts."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        spotify_service=None,
        verbose: bool = False
    ):
        """Initialize the mood analyzer agent.

        Args:
            llm: Language model for mood analysis
            spotify_service: SpotifyService for artist discovery
            verbose: Whether to enable verbose logging
        """
        super().__init__(
            name="mood_analyzer",
            description="Analyzes user mood prompts and translates them into audio features and search parameters",
            llm=llm,
            verbose=verbose
        )
        
        self.spotify_service = spotify_service

        # Enhanced mood analysis prompts with full RecoBeat API feature set
        self.system_prompt = """You are an expert music curator and audio analyst. Your task is to analyze user mood prompts and translate them into comprehensive audio feature profiles for music recommendations.

Analyze the user's mood description and provide:
1. A clear interpretation of their desired mood and atmosphere
2. Comprehensive audio feature targets using all available features
3. Feature importance weights for different aspects of the mood
4. Keywords for searching relevant artists and genres
5. Specific artist recommendations (if mentioned by name)
6. Genre keywords for track-based discovery
7. Reasoning for your audio feature choices

Available Audio Features (use ranges [min, max] for each):
- acousticness (0-1): Acoustic vs electronic elements (0=electronic/synthetic, 1=acoustic/natural)
- danceability (0-1): Suitability for dancing (0=not danceable, 1=very danceable)
- energy (0-1): Intensity and activity level (0=calm/relaxed, 1=intense/powerful)
- instrumentalness (0-1): Vocal vs instrumental content (0=likely vocal, 1=likely instrumental)
- key (-1-11): Musical key (0=C, 1=C#/Db, 2=D, etc., -1=no key detected)
- liveness (0-1): Probability of live performance (0=studio, 1=live recording)
- loudness (-60-2): Overall loudness in decibels (lower=more dynamic range)
- mode (0-1): Major (1) vs minor (0) tonality (1=happier/brighter, 0=sadder/darker)
- speechiness (0-1): Presence of spoken words (0=no speech, 1=mostly speech)
- tempo (0-250): Estimated tempo in BPM (beats per minute)
- valence (0-1): Musical positiveness (0=sad/negative, 1=happy/positive)
- popularity (0-100): Track popularity (0=underground, 100=mainstream)

Example mood analysis:
For "super indie" you might target:
- High acousticness [0.7, 1.0] (natural, organic sound)
- Low-moderate energy [0.2, 0.5] (mellow, not intense)
- Low popularity [0, 25] (underground artists)
- Moderate instrumentalness [0.3, 0.8] (less mainstream pop vocals)
- Natural tempo range [60, 120] (not extreme BPM)
- Lower loudness [-20, -8] (more dynamic range)

CRITICAL: Always suggest specific artist names that match the mood:
- artist_recommendations: ALWAYS provide 3-8 specific artist names that match the mood, even if not mentioned by user
  * For "city pop": suggest artists like "Miki Matsubara", "Tatsuro Yamashita", "Mariya Takeuchi"
  * For "french funk": suggest artists like "Daft Punk", "Justice", "Vulfpeck", "Parcels"
  * For niche genres: research and suggest authentic artists from that scene
  * This is CRUCIAL for artist discovery - empty list severely degrades recommendations
- genre_keywords: Genre terms and mood descriptors (e.g., "indie", "city pop", "jazz", "electronic", "chill")

Provide your analysis in valid JSON format with this structure:
{
  "mood_interpretation": "Clear description of the intended mood",
  "primary_emotion": "main emotional character",
  "energy_level": "overall intensity description",
  "target_features": {
    "feature_name": [min_value, max_value],
    "acousticness": [0.7, 1.0],
    ...
  },
  "feature_weights": {
    "feature_name": importance_0_to_1,
    "acousticness": 0.9,
    ...
  },
  "search_keywords": ["indie", "alternative", "underground"],
  "artist_recommendations": ["Artist Name 1", "Artist Name 2"],
  "genre_keywords": ["indie", "alternative", "rock"],
  "reasoning": "Explanation of feature choices and mood interpretation"
}"""

    async def execute(self, state: AgentState) -> AgentState:
        """Execute mood analysis on the user's prompt.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with mood analysis
        """
        try:
            logger.info(f"Analyzing mood prompt: {state.mood_prompt}")

            # Use LLM for mood analysis
            if self.llm:
                mood_analysis = await self._analyze_mood_with_llm(state.mood_prompt)
            else:
                # Fallback rule-based analysis
                mood_analysis = self._analyze_mood_fallback(state.mood_prompt)

            # Update state with analysis
            state.mood_analysis = mood_analysis
            state.current_step = "mood_analyzed"
            state.status = RecommendationStatus.ANALYZING_MOOD

            # Extract target features and weights for recommendations
            target_features = self._extract_target_features(mood_analysis)
            feature_weights = self._extract_feature_weights(mood_analysis)

            # Store in metadata for use by other agents
            if "target_features" not in state.metadata:
                state.metadata["target_features"] = {}
            if "feature_weights" not in state.metadata:
                state.metadata["feature_weights"] = {}

            state.metadata["target_features"].update(target_features)
            state.metadata["feature_weights"].update(feature_weights)

            # Also store mood analysis details for reference
            state.metadata["mood_interpretation"] = mood_analysis.get("mood_interpretation", "")
            state.metadata["primary_emotion"] = mood_analysis.get("primary_emotion", "neutral")
            state.metadata["search_keywords"] = mood_analysis.get("search_keywords", [])
            state.metadata["artist_recommendations"] = mood_analysis.get("artist_recommendations", [])
            state.metadata["genre_keywords"] = mood_analysis.get("genre_keywords", [])

            logger.info(f"Mood analysis completed for prompt: {state.mood_prompt}")
            logger.info(f"Target features: {list(target_features.keys())}")
            logger.info(f"Feature weights: {feature_weights}")

            # Determine playlist target plan based on mood
            playlist_target = self._determine_playlist_target(
                state.mood_prompt,
                mood_analysis,
                target_features
            )
            state.metadata["playlist_target"] = playlist_target

            logger.info(
                f"Playlist target: {playlist_target['target_count']} tracks "
                f"(min: {playlist_target['min_count']}, max: {playlist_target['max_count']}) - "
                f"{playlist_target['reasoning']}"
            )

            # Discover artists matching the mood (if Spotify service available)
            if self.spotify_service:
                await self._discover_mood_artists(state, mood_analysis)

        except Exception as e:
            logger.error(f"Error in mood analysis: {str(e)}", exc_info=True)
            state.set_error(f"Mood analysis failed: {str(e)}")

        return state

    async def _analyze_mood_with_llm(self, mood_prompt: str) -> Dict[str, Any]:
        """Analyze mood using LLM.

        Args:
            mood_prompt: User's mood description

        Returns:
            Comprehensive mood analysis
        """
        try:
            # Create prompt
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Analyze this mood: '{mood_prompt}'"}
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Try to parse JSON response
            try:
                # Extract JSON from response
                content = response.content if hasattr(response, 'content') else str(response)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # Fallback if no JSON found
                    analysis = self._parse_llm_response_fallback(content)

            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.error(f"JSON parsing failed: {response}")
                analysis = self._parse_llm_response_fallback(response)

            return analysis

        except Exception as e:
            logger.error(f"LLM mood analysis failed: {str(e)}")
            return self._analyze_mood_fallback(mood_prompt)

    def _analyze_mood_fallback(self, mood_prompt: str) -> Dict[str, Any]:
        """Enhanced fallback rule-based mood analysis with full feature set.

        Args:
            mood_prompt: User's mood description

        Returns:
            Comprehensive mood analysis with all 12 audio features
        """
        prompt_lower = mood_prompt.lower()

        # Enhanced analysis structure
        analysis = {
            "mood_interpretation": f"Rule-based analysis of: {mood_prompt}",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "feature_weights": {},
            "search_keywords": [],
            "artist_recommendations": [],
            "genre_keywords": [],
            "reasoning": f"Rule-based analysis using keyword matching for: {mood_prompt}"
        }

        # Define mood profiles for common scenarios
        mood_profiles = {
            "indie": {
                "keywords": ["indie", "alternative", "underground", "independent"],
                "features": {
                    "acousticness": [0.6, 1.0],
                    "energy": [0.2, 0.6],
                    "popularity": [0, 40],
                    "loudness": [-20, -5],
                    "instrumentalness": [0.2, 0.8]
                },
                "weights": {"acousticness": 0.9, "popularity": 0.8, "energy": 0.7}
            },
            "party": {
                "keywords": ["party", "celebration", "dance", "club", "energetic"],
                "features": {
                    "energy": [0.7, 1.0],
                    "danceability": [0.7, 1.0],
                    "valence": [0.6, 1.0],
                    "tempo": [110, 140],
                    "loudness": [-10, -2]
                },
                "weights": {"energy": 0.9, "danceability": 0.9, "valence": 0.8}
            },
            "chill": {
                "keywords": ["chill", "relaxed", "calm", "peaceful", "mellow"],
                "features": {
                    "energy": [0.0, 0.4],
                    "acousticness": [0.5, 1.0],
                    "valence": [0.4, 0.8],
                    "tempo": [60, 100],
                    "loudness": [-25, -10]
                },
                "weights": {"energy": 0.9, "acousticness": 0.8, "tempo": 0.7}
            },
            "focus": {
                "keywords": ["focus", "concentration", "study", "instrumental", "ambient"],
                "features": {
                    "instrumentalness": [0.7, 1.0],
                    "energy": [0.1, 0.4],
                    "acousticness": [0.4, 1.0],
                    "speechiness": [0.0, 0.2],
                    "tempo": [50, 90]
                },
                "weights": {"instrumentalness": 0.9, "speechiness": 0.8, "energy": 0.7}
            },
            "emotional": {
                "keywords": ["emotional", "sad", "melancholy", "deep", "sentimental"],
                "features": {
                    "valence": [0.0, 0.4],
                    "energy": [0.1, 0.5],
                    "mode": [0, 0.3],  # Minor key preference
                    "acousticness": [0.4, 1.0],
                    "tempo": [60, 110]
                },
                "weights": {"valence": 0.9, "mode": 0.8, "acousticness": 0.7}
            }
        }

        # Check for mood profile matches
        matched_profiles = []
        for mood_name, profile in mood_profiles.items():
            if any(keyword in prompt_lower for keyword in profile["keywords"]):
                matched_profiles.append((mood_name, profile))

        # Apply matched profiles
        if matched_profiles:
            for mood_name, profile in matched_profiles:
                analysis["mood_interpretation"] = f"{mood_name.capitalize()} mood based on: {mood_prompt}"
                analysis["target_features"].update(profile["features"])
                analysis["feature_weights"].update(profile["weights"])

                # Update primary emotion based on mood
                emotion_mapping = {
                    "party": "positive",
                    "chill": "neutral",
                    "focus": "neutral",
                    "emotional": "negative",
                    "indie": "neutral"
                }
                if mood_name in emotion_mapping:
                    analysis["primary_emotion"] = emotion_mapping[mood_name]

        # Additional keyword-based feature analysis
        self._enhance_features_with_keywords(analysis, prompt_lower)

        # Generate search keywords
        analysis["search_keywords"] = self._extract_search_keywords(mood_prompt)
        
        # Extract genre keywords and artist recommendations
        genre_keywords, artist_recommendations = self._extract_genres_and_artists(mood_prompt)
        analysis["genre_keywords"] = genre_keywords
        analysis["artist_recommendations"] = artist_recommendations

        return analysis

    def _enhance_features_with_keywords(self, analysis: Dict[str, Any], prompt_lower: str):
        """Enhance feature analysis with specific keywords."""
        # Energy analysis
        high_energy_keywords = ["energetic", "upbeat", "exciting", "workout", "intense", "powerful", "hype"]
        low_energy_keywords = ["calm", "peaceful", "sleepy", "soft", "gentle", "laid-back"]

        if any(keyword in prompt_lower for keyword in high_energy_keywords):
            analysis["energy_level"] = "high"
            if "energy" not in analysis["target_features"]:
                analysis["target_features"]["energy"] = [0.7, 1.0]
                analysis["target_features"]["valence"] = [0.5, 1.0]
        elif any(keyword in prompt_lower for keyword in low_energy_keywords):
            analysis["energy_level"] = "low"
            if "energy" not in analysis["target_features"]:
                analysis["target_features"]["energy"] = [0.0, 0.4]

        # Valence analysis
        positive_keywords = ["happy", "joyful", "cheerful", "uplifting", "fun", "bright"]
        negative_keywords = ["sad", "depressed", "dark", "moody", "bittersweet"]

        if any(keyword in prompt_lower for keyword in positive_keywords):
            analysis["primary_emotion"] = "positive"
            if "valence" not in analysis["target_features"]:
                analysis["target_features"]["valence"] = [0.7, 1.0]
        elif any(keyword in prompt_lower for keyword in negative_keywords):
            analysis["primary_emotion"] = "negative"
            if "valence" not in analysis["target_features"]:
                analysis["target_features"]["valence"] = [0.0, 0.4]

        # Danceability analysis
        dance_keywords = ["dance", "dancing", "groove", "rhythm", "club"]
        if any(keyword in prompt_lower for keyword in dance_keywords):
            if "danceability" not in analysis["target_features"]:
                analysis["target_features"]["danceability"] = [0.6, 1.0]

        # Acousticness analysis
        acoustic_keywords = ["acoustic", "unplugged", "organic", "folk", "singer-songwriter"]
        if any(keyword in prompt_lower for keyword in acoustic_keywords):
            if "acousticness" not in analysis["target_features"]:
                analysis["target_features"]["acousticness"] = [0.7, 1.0]

        # Instrumentalness analysis
        instrumental_keywords = ["instrumental", "no vocals", "background", "ambient"]
        if any(keyword in prompt_lower for keyword in instrumental_keywords):
            if "instrumentalness" not in analysis["target_features"]:
                analysis["target_features"]["instrumentalness"] = [0.7, 1.0]

        # Live performance analysis
        live_keywords = ["live", "concert", "performance", "audience"]
        if any(keyword in prompt_lower for keyword in live_keywords):
            if "liveness" not in analysis["target_features"]:
                analysis["target_features"]["liveness"] = [0.6, 1.0]

        # Speech/Talk analysis
        speech_keywords = ["podcast", "talk", "spoken", "narrative", "story"]
        if any(keyword in prompt_lower for keyword in speech_keywords):
            if "speechiness" not in analysis["target_features"]:
                analysis["target_features"]["speechiness"] = [0.5, 1.0]

    def _parse_llm_response_fallback(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response when JSON parsing fails.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed mood analysis
        """
        content_lower = response_content.lower()

        analysis = {
            "mood_interpretation": response_content[:200] + "...",
            "primary_emotion": "neutral",
            "energy_level": "medium",
            "target_features": {},
            "search_keywords": [],
            "reasoning": response_content
        }

        # Extract basic features from text
        if "high energy" in content_lower or "energetic" in content_lower:
            analysis["energy_level"] = "high"
            analysis["target_features"]["energy"] = [0.7, 1.0]

        if "low energy" in content_lower or "calm" in content_lower:
            analysis["energy_level"] = "low"
            analysis["target_features"]["energy"] = [0.0, 0.4]

        if "happy" in content_lower or "positive" in content_lower:
            analysis["primary_emotion"] = "positive"
            analysis["target_features"]["valence"] = [0.7, 1.0]

        if "sad" in content_lower or "negative" in content_lower:
            analysis["primary_emotion"] = "negative"
            analysis["target_features"]["valence"] = [0.0, 0.4]

        return analysis

    def _extract_target_features(self, mood_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract target audio features from mood analysis with full feature set support.

        Args:
            mood_analysis: Comprehensive mood analysis

        Returns:
            Dictionary of target audio features (midpoint of ranges)
        """
        target_features = {}

        features = mood_analysis.get("target_features", {})

        # Convert ranges to target values (use midpoint)
        for feature, value_range in features.items():
            if isinstance(value_range, list) and len(value_range) == 2:
                # Use midpoint of range as target value
                target_features[feature] = sum(value_range) / 2
            elif isinstance(value_range, (int, float)):
                target_features[feature] = float(value_range)

        # Ensure we have reasonable defaults for key features if missing
        if not target_features:
            logger.warning("No target features extracted from mood analysis")
            # Set neutral defaults
            target_features = {
                "energy": 0.5,
                "valence": 0.5,
                "danceability": 0.5,
                "acousticness": 0.5
            }

        logger.info(f"Extracted target features: {list(target_features.keys())}")
        return target_features

    def _extract_feature_weights(self, mood_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract feature importance weights from mood analysis.

        Args:
            mood_analysis: Comprehensive mood analysis

        Returns:
            Dictionary of feature weights (0-1 importance)
        """
        feature_weights = mood_analysis.get("feature_weights", {})

        # Set default weights if none provided
        if not feature_weights:
            # Default weights favoring core mood features
            feature_weights = {
                "energy": 0.8,
                "valence": 0.8,
                "danceability": 0.6,
                "acousticness": 0.6,
                "instrumentalness": 0.5,
                "tempo": 0.4,
                "mode": 0.4,
                "loudness": 0.3,
                "speechiness": 0.3,
                "liveness": 0.2,
                "key": 0.2,
                "popularity": 0.1
            }

        return feature_weights

    def _extract_search_keywords(self, mood_prompt: str) -> List[str]:
        """Extract search keywords from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            List of relevant search keywords
        """
        # Simple keyword extraction - can be enhanced with NLP
        keywords = []

        # Split by common delimiters
        words = mood_prompt.replace(",", " ").replace(" and ", " ").split()

        # Filter meaningful words (length > 3, not common stop words)
        stop_words = {"for", "with", "that", "this", "very", "some", "music", "songs", "playlist"}
        meaningful_words = [
            word.lower() for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]

        keywords.extend(meaningful_words)

        # Add some common mood-related terms
        mood_synonyms = {
            "chill": ["relaxed", "laid-back", "mellow"],
            "energetic": ["upbeat", "lively", "dynamic"],
            "sad": ["melancholy", "emotional", "bittersweet"],
            "happy": ["joyful", "cheerful", "uplifting"],
            "romantic": ["love", "intimate", "passionate"],
            "focus": ["concentration", "study", "instrumental"],
            "party": ["celebration", "fun", "dance"],
            "workout": ["fitness", "motivation", "pump"],
        }

        for word in meaningful_words:
            if word in mood_synonyms:
                keywords.extend(mood_synonyms[word])

        return list(set(keywords))  # Remove duplicates

    def _extract_genres_and_artists(self, mood_prompt: str) -> tuple[List[str], List[str]]:
        """Extract genre keywords and artist names from mood prompt.

        Args:
            mood_prompt: User's mood description

        Returns:
            Tuple of (genre_keywords, artist_recommendations)
        """
        # Common genre keywords that should be searched as genres
        known_genres = {
            "indie", "rock", "pop", "jazz", "electronic", "edm", "hip-hop", "hip hop",
            "rap", "r&b", "rnb", "soul", "funk", "disco", "house", "techno", "trance",
            "dubstep", "drum and bass", "dnb", "ambient", "classical", "country", "folk",
            "metal", "punk", "alternative", "grunge", "ska", "reggae", "blues", "gospel",
            "latin", "salsa", "bossa nova", "samba", "k-pop", "kpop", "j-pop", "jpop",
            "city pop", "citypop", "synthwave", "vaporwave", "lo-fi", "lofi", "chillwave",
            "shoegaze", "post-rock", "post-punk", "new wave", "psychedelic", "progressive"
        }

        prompt_lower = mood_prompt.lower()
        genre_keywords = []
        artist_recommendations = []

        # Check for known genres
        for genre in known_genres:
            if genre in prompt_lower:
                # Normalize genre (remove spaces for search)
                normalized_genre = genre.replace(" ", "").replace("-", "")
                genre_keywords.append(normalized_genre)

        # Simple heuristic: Look for capitalized words that might be artist names
        # This is a basic approach - could be enhanced with NLP/entity recognition
        words = mood_prompt.split()
        for i, word in enumerate(words):
            # Check if word is capitalized (and not at start of sentence)
            if word and word[0].isupper() and i > 0:
                # Check if it's part of a multi-word name
                potential_artist = word
                # Look ahead for more capitalized words
                j = i + 1
                while j < len(words) and words[j] and words[j][0].isupper():
                    potential_artist += " " + words[j]
                    j += 1
                
                # Only add if not a genre keyword
                if potential_artist.lower() not in known_genres:
                    artist_recommendations.append(potential_artist)

        # Remove duplicates
        genre_keywords = list(set(genre_keywords))
        artist_recommendations = list(set(artist_recommendations))

        return genre_keywords, artist_recommendations

    def _determine_playlist_target(
        self,
        mood_prompt: str,
        mood_analysis: Dict[str, Any],
        target_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine target playlist size and quality thresholds based on mood.
        
        Args:
            mood_prompt: User's mood description
            mood_analysis: Analyzed mood information
            target_features: Target audio features
            
        Returns:
            Playlist target plan with size, thresholds, and reasoning
        """
        # Default targets
        target_count = 20
        min_count = 15
        max_count = 25
        quality_threshold = 0.75
        
        # Analyze mood complexity and specificity
        feature_count = len(target_features)
        high_weight_features = sum(1 for w in mood_analysis.get("feature_weights", {}).values() if w > 0.7)
        
        # Adjust based on mood specificity
        if feature_count <= 4 or high_weight_features <= 2:
            # Broad mood (e.g., "chill") - more tracks possible
            target_count = 25
            max_count = 30
            quality_threshold = 0.7
            reasoning = "Broad mood allows for larger, more diverse playlist"
        elif feature_count >= 8 or high_weight_features >= 4:
            # Very specific mood (e.g., "super indie acoustic") - fewer, more focused
            target_count = 18
            min_count = 12
            quality_threshold = 0.8
            reasoning = "Specific mood requires focused, high-quality selection"
        else:
            # Moderate specificity
            target_count = 20
            quality_threshold = 0.75
            reasoning = "Balanced target for moderate mood specificity"
        
        # Check for niche indicators in prompt
        niche_keywords = ["indie", "underground", "obscure", "niche", "rare"]
        if any(keyword in mood_prompt.lower() for keyword in niche_keywords):
            target_count = min(target_count, 20)
            min_count = 12
            reasoning += " (niche mood may have limited matches)"
        
        return {
            "target_count": target_count,
            "min_count": min_count,
            "max_count": max_count,
            "quality_threshold": quality_threshold,
            "reasoning": reasoning
        }

    async def _discover_mood_artists(self, state: AgentState, mood_analysis: Dict[str, Any]):
        """Discover artists matching the mood using Spotify search and LLM filtering.

        Args:
            state: Current agent state
            mood_analysis: Mood analysis results
        """
        try:
            logger.info("Starting artist discovery for mood")

            # Get access token
            access_token = state.metadata.get("spotify_access_token")
            if not access_token:
                logger.warning("No Spotify access token available for artist discovery")
                return

            # Get genre keywords and artist recommendations from mood analysis
            genre_keywords = mood_analysis.get("genre_keywords", [])
            artist_recommendations = mood_analysis.get("artist_recommendations", [])
            
            # Fallback to search keywords if no specific genres/artists identified
            search_keywords = mood_analysis.get("search_keywords", [])
            if not genre_keywords and not artist_recommendations and not search_keywords:
                search_keywords = self._extract_search_keywords(state.mood_prompt)

            all_artists = []

            # 1. Search for artists by name (direct artist search)
            for artist_name in artist_recommendations[:3]:  # Limit to top 3 artist names
                try:
                    logger.info(f"Searching for artist: {artist_name}")
                    artists = await self.spotify_service.search_spotify_artists(
                        access_token=access_token,
                        query=artist_name,
                        limit=3  # Few results per artist name
                    )
                    all_artists.extend(artists)
                except Exception as e:
                    logger.error(f"Failed to search for artist '{artist_name}': {e}")

            # 2. Search tracks for genre keywords and extract artists
            for genre in genre_keywords[:3]:  # Limit to top 3 genres
                try:
                    logger.info(f"Searching tracks for genre: {genre}")
                    # Use genre filter format for better results
                    query = f"genre:{genre}"
                    artists = await self.spotify_service.search_tracks_for_artists(
                        access_token=access_token,
                        query=query,
                        limit=15  # More tracks to get diverse artists
                    )
                    all_artists.extend(artists)
                except Exception as e:
                    logger.error(f"Failed to search tracks for genre '{genre}': {e}")

            # 3. Fallback: use general search keywords with artist search
            if not all_artists and search_keywords:
                for keyword in search_keywords[:3]:
                    try:
                        artists = await self.spotify_service.search_spotify_artists(
                            access_token=access_token,
                            query=keyword,
                            limit=8
                        )
                        all_artists.extend(artists)
                    except Exception as e:
                        logger.error(f"Failed to search artists for keyword '{keyword}': {e}")

            if not all_artists:
                logger.warning("No artists found during discovery")
                return

            # Remove duplicates
            seen_ids = set()
            unique_artists = []
            for artist in all_artists:
                artist_id = artist.get("id")
                if artist_id and artist_id not in seen_ids:
                    seen_ids.add(artist_id)
                    unique_artists.append(artist)

            logger.info(f"Found {len(unique_artists)} unique artists from search")

            # Use LLM to filter artists if available
            if self.llm and len(unique_artists) > 6:
                filtered_artists = await self._llm_filter_artists(
                    unique_artists, state.mood_prompt, mood_analysis
                )
            else:
                # Just take top artists by popularity if no LLM
                filtered_artists = sorted(
                    unique_artists,
                    key=lambda x: x.get("popularity", 0),
                    reverse=True
                )[:8]  # Reduced from 12 to 8 for focused playlists

            # Store in state metadata
            state.metadata["discovered_artists"] = [
                {
                    "id": artist.get("id"),
                    "name": artist.get("name"),
                    "genres": artist.get("genres", []),
                    "popularity": artist.get("popularity", 50)
                }
                for artist in filtered_artists
            ]
            state.metadata["mood_matched_artists"] = [artist.get("id") for artist in filtered_artists]

            logger.info(f"Discovered {len(filtered_artists)} mood-matched artists: {[a.get('name') for a in filtered_artists[:5]]}")

        except Exception as e:
            logger.error(f"Error in artist discovery: {str(e)}", exc_info=True)
            # Don't fail the whole pipeline, just continue without artist discovery

    async def _llm_filter_artists(
        self,
        artists: List[Dict[str, Any]],
        mood_prompt: str,
        mood_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to filter and select artists that best match the mood.

        Args:
            artists: List of artist candidates
            mood_prompt: User's mood description
            mood_analysis: Mood analysis results

        Returns:
            Filtered list of artists (8-12 artists)
        """
        try:
            # Prepare artist summary for LLM
            artists_summary = []
            for i, artist in enumerate(artists[:20], 1):  # Limit to 20 for LLM context
                genres_str = ", ".join(artist.get("genres", [])[:3]) or "no genres listed"
                artists_summary.append(
                    f"{i}. {artist.get('name')} - Genres: {genres_str}, Popularity: {artist.get('popularity', 50)}"
                )

            mood_interpretation = mood_analysis.get("mood_interpretation", mood_prompt)

            prompt = f"""You are a music curator selecting artists that match a specific mood.

**User's Mood**: "{mood_prompt}"

**Mood Analysis**: {mood_interpretation}

**Available Artists**:
{chr(10).join(artists_summary)}

**Task**: Select 6-8 artists from the list that best match this mood. Consider:
1. Genre compatibility with the mood
2. Artist style and vibe
3. Mix of popular and lesser-known artists for variety
4. Overall cohesion with the requested mood

Respond in JSON format:
{{
  "selected_artist_indices": [1, 3, 5, ...],
  "reasoning": "Brief explanation of why these artists fit the mood"
}}

Select artist indices (numbers from the list above)."""

            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse JSON response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)

                selected_indices = result.get("selected_artist_indices", [])
                reasoning = result.get("reasoning", "")

                # Map indices to artists (1-indexed in prompt, 0-indexed in list)
                filtered_artists = [
                    artists[idx - 1] for idx in selected_indices
                    if 1 <= idx <= len(artists)
                ]

                # Store reasoning in state metadata
                if hasattr(self, '_current_state'):
                    self._current_state.metadata["artist_discovery_reasoning"] = reasoning

                logger.info(f"LLM selected {len(filtered_artists)} artists: {reasoning}")
                return filtered_artists[:12]  # Cap at 12

            else:
                logger.warning("Could not parse LLM artist filtering response")
                return artists[:12]

        except Exception as e:
            logger.error(f"LLM artist filtering failed: {str(e)}")
            # Fallback to popularity-based selection
            return sorted(artists, key=lambda x: x.get("popularity", 0), reverse=True)[:12]