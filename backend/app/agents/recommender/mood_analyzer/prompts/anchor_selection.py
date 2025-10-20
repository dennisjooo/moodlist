"""Prompts for LLM-guided anchor track selection."""

from typing import Dict, Any, List


def get_anchor_strategy_prompt(
    mood_prompt: str,
    mood_analysis: Dict[str, Any],
    genre_keywords: List[str],
    target_features: Dict[str, Any],
    available_tracks: List[Dict[str, Any]]
) -> str:
    """Get prompt for determining anchor track selection strategy.

    Args:
        mood_prompt: User's original mood description
        mood_analysis: Full mood analysis results
        genre_keywords: List of genre keywords
        target_features: Target audio features
        available_tracks: List of candidate tracks with their features

    Returns:
        Prompt string for anchor track strategy
    """
    genres_str = ', '.join(genre_keywords) if genre_keywords else 'None'
    artists_str = ', '.join(mood_analysis.get('artist_recommendations', [])) if mood_analysis.get('artist_recommendations') else 'None'

    # Format available tracks info
    tracks_info = []
    for i, track in enumerate(available_tracks[:20]):  # Limit to 20 for prompt size
        artists = [a.get('name', '') for a in track.get('artists', [])]
        artist_str = ', '.join(artists) if artists else 'Unknown'
        features = track.get('audio_features', {})

        track_info = f"{i+1}. '{track.get('name', 'Unknown')}' by {artist_str}"
        if features:
            key_features = {k: v for k, v in features.items()
                          if k in ['danceability', 'energy', 'valence', 'tempo', 'instrumentalness']}
            track_info += f" - Features: {key_features}"
        tracks_info.append(track_info)

    tracks_context = '\n'.join(tracks_info)

    return f"""Analyze this music request and determine the optimal strategy for selecting ANCHOR TRACKS.

User's request: "{mood_prompt}"

Mood Analysis Summary:
- Primary emotion: {mood_analysis.get('primary_emotion', 'Unknown')}
- Genres: {genres_str}
- Artists: {artists_str}
- Target features: {target_features}

Available candidate tracks ({len(available_tracks)} total):
{tracks_context}

ANCHOR TRACKS serve as reference points for playlist generation. They should:
1. Strongly represent the core mood/genre requested
2. Have high audio feature alignment with target features
3. Be popular/well-known tracks that set the right tone
4. Provide diversity while maintaining cohesion
5. Include user-mentioned tracks if any were specified

Task: Determine the best strategy for selecting anchor tracks. Consider:
- How many anchor tracks are optimal (typically 3-8)
- Which tracks should be prioritized (user-mentioned first, then genre representatives)
- What criteria should be used for scoring (feature alignment, popularity, genre fit)
- Any special considerations for this mood/genre combination

Respond in JSON format:
{{
  "anchor_count": 5,
  "selection_criteria": {{
    "prioritize_user_mentioned": true,
    "feature_weights": {{
      "danceability": 1.0,
      "energy": 0.9,
      "valence": 0.8,
      "tempo": 0.9,
      "instrumentalness": 0.7
    }},
    "popularity_weight": 0.3,
    "genre_diversity": true
  }},
  "track_priorities": [
    {{
      "track_index": 0,
      "reason": "Strong feature match and represents core genre",
      "priority_score": 0.95
    }}
  ],
  "strategy_notes": "Focus on high-energy dance tracks with strong groove"
}}

The anchor_count should be between 3-8. Higher counts work for diverse moods, lower for very specific requests."""


def get_anchor_scoring_prompt(
    track_candidates: List[Dict[str, Any]],
    target_features: Dict[str, Any],
    selection_criteria: Dict[str, Any]
) -> str:
    """Get prompt for scoring anchor track candidates.

    Args:
        track_candidates: List of tracks to score
        target_features: Target audio features from mood analysis
        mood_context: Mood analysis context
        selection_criteria: Criteria determined by strategy prompt

    Returns:
        Prompt string for scoring tracks
    """
    # Format track candidates
    candidates_info = []
    for i, candidate in enumerate(track_candidates):
        track = candidate.get('track', {})
        artists = [a.get('name', '') for a in track.get('artists', [])]
        artist_str = ', '.join(artists) if artists else 'Unknown'

        features = candidate.get('features', {})
        source = candidate.get('source', 'unknown')
        user_mentioned = candidate.get('user_mentioned', False)

        candidate_info = f"{i+1}. '{track.get('name', 'Unknown')}' by {artist_str}"
        candidate_info += f" (Source: {source})"
        if user_mentioned:
            candidate_info += " [USER MENTIONED]"

        if features:
            key_features = {k: round(float(v), 3) for k, v in features.items()
                          if k in ['danceability', 'energy', 'valence', 'tempo', 'instrumentalness']}
            candidate_info += f" - Features: {key_features}"

        candidates_info.append(candidate_info)

    candidates_context = '\n'.join(candidates_info)

    return f"""Score these track candidates for use as ANCHOR TRACKS in a playlist.

Target mood features: {target_features}
Selection criteria: {selection_criteria}

Track candidates:
{candidates_context}

ANCHOR TRACK scoring should consider:
1. Feature alignment with mood targets (danceability, energy, valence, tempo, etc.)
2. Genre/style fit for the requested mood
3. Popularity and recognizability
4. User-mentioned tracks get highest priority
5. Diversity while maintaining mood cohesion
6. Audio quality and production values

Score each track from 0.0 to 1.0, where:
- 1.0 = Perfect anchor track (excellent feature match, high quality, strong mood fit)
- 0.8 = Very good anchor track
- 0.6 = Good anchor track
- 0.4 = Acceptable but not ideal
- 0.2 = Poor fit, should be avoided

Respond in JSON format:
{{
  "track_scores": [
    {{
      "track_index": 0,
      "score": 0.95,
      "confidence": 0.9,
      "reasoning": "Excellent feature match and represents the core mood perfectly"
    }}
  ],
  "selection_notes": "Prioritize tracks with strong groove and energy matching the French funk vibe"
}}

Only score tracks that would make good anchor tracks. Be selective - not all candidates need high scores."""


def get_anchor_finalization_prompt(
    scored_candidates: List[Dict[str, Any]],
    target_count: int,
    mood_context: Dict[str, Any]
) -> str:
    """Get prompt for finalizing anchor track selection.

    Args:
        scored_candidates: Tracks with LLM-assigned scores
        target_count: Target number of anchor tracks
        mood_context: Mood analysis context

    Returns:
        Prompt string for final selection
    """
    # Format scored candidates
    candidates_info = []
    for candidate in scored_candidates:
        track_index = candidate.get('track_index', 0)
        score = candidate.get('score', 0.0)
        reasoning = candidate.get('reasoning', '')

        original_track = candidate.get('original_candidate', {})
        track = original_track.get('track', {})
        artists = [a.get('name', '') for a in track.get('artists', [])]
        artist_str = ', '.join(artists) if artists else 'Unknown'

        candidate_info = f"Track {track_index}: '{track.get('name', 'Unknown')}' by {artist_str}"
        candidate_info += f" - Score: {score:.2f} - {reasoning}"
        candidates_info.append(candidate_info)

    candidates_context = '\n'.join(candidates_info)

    return f"""Finalize the selection of ANCHOR TRACKS from these scored candidates.

Target number of anchors: {target_count}
Mood context: {mood_context.get('mood_interpretation', '')}

Scored candidates:
{candidates_context}

Select the {target_count} best tracks to serve as anchors. Consider:
1. Score quality and ranking
2. Diversity of artists/genres while maintaining mood cohesion
3. Balance between user-mentioned tracks and genre representatives
4. Overall playlist flow and energy progression
5. Feature variety that provides good reference points for recommendations

Respond in JSON format:
{{
  "selected_indices": [0, 1, 2, 4, 6],
  "selection_reasoning": "Selected tracks provide excellent feature diversity and strong mood representation",
  "anchor_characteristics": {{
    "energy_range": "moderate to high",
    "key_diversity": "good mix",
    "genre_coverage": "french funk with electronic elements",
    "user_mentioned_count": 2
  }}
}}

The selected_indices should correspond to the track indices from the scored candidates list."""
