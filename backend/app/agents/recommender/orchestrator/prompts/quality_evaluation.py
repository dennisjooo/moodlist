"""Prompt templates for quality evaluation."""


def get_quality_evaluation_prompt(
    mood_prompt: str,
    mood_interpretation: str,
    artist_recommendations: list,
    genre_keywords: list,
    target_features: dict,
    tracks_summary: str,
    target_count: int,
    evaluation: dict,
    user_mentioned_tracks: list = None
) -> str:
    """Get the prompt for evaluating playlist quality.
    
    Args:
        mood_prompt: User's original mood request
        mood_interpretation: Analyzed mood interpretation
        artist_recommendations: List of expected artists
        genre_keywords: List of expected genres
        target_features: Target audio features
        tracks_summary: Summary of tracks in the playlist
        target_count: Target number of tracks
        evaluation: Algorithmic evaluation results
        user_mentioned_tracks: List of tracks explicitly mentioned by user (protected)
        
    Returns:
        Prompt string for LLM quality evaluation
    """
    # Build user favorites section if applicable
    user_favorites_section = ""
    if user_mentioned_tracks:
        user_favorites_section = f"""
**USER FAVORITES (PROTECTED)**: The following tracks were explicitly mentioned by the user and MUST stay in the playlist:
{chr(10).join(f'- {track}' for track in user_mentioned_tracks)}

⚠️ DO NOT flag these tracks as outliers or suggest removal, even if they seem to not fit perfectly.
"""
    
    return f"""You are a STRICT music curator expert evaluating a playlist for quality and cohesion.

**User's Mood Request**: "{mood_prompt}"

**Mood Analysis**: {mood_interpretation}
{user_favorites_section}
**Expected Artists**: {', '.join(artist_recommendations[:8])}
**Expected Genres**: {', '.join(genre_keywords[:5])}

**Target Audio Features**: {', '.join(f'{k}={v:.2f}' if isinstance(v, (int, float)) else f'{k}={v}' for k, v in list(target_features.items())[:5])}

**Playlist** ({len(tracks_summary.split(chr(10)))} tracks, target: {target_count}):
{tracks_summary}

**Algorithmic Metrics**:
- Cohesion Score: {evaluation['cohesion_score']:.2f}/1.0
- Confidence Score: {evaluation['confidence_score']:.2f}/1.0
- Diversity Score: {evaluation['diversity_score']:.2f}/1.0
- Outliers Found: {len(evaluation['outlier_tracks'])}
- Overall Score: {evaluation['overall_score']:.2f}/1.0

**Task**: BE STRICT - Evaluate if this playlist truly matches the user's mood. Consider:
1. **Language Match**: Do track/artist names match the expected language/region? (e.g., Spanish tracks for French funk = REJECT)
2. **Genre Match**: Do tracks fit the genre/style requested? Flag any that feel wrong.
3. **Artist Match**: Are artists similar to the expected ones listed above?
4. **Flow**: Would these tracks flow well together without jarring shifts?

**CRITICAL**: Flag ANY track that doesn't match the language, genre, or cultural style of the mood request.
For example:
- Latin/Spanish music in a French playlist = OUT OF PLACE
- K-pop in a British indie playlist = OUT OF PLACE
- Regional Mexican music in an electronic playlist = OUT OF PLACE
- Indonesian/Malay tracks in an English trap/R&B playlist = OUT OF PLACE
- Italian rap in a US hip-hop playlist = OUT OF PLACE
- Unknown artists with no genre fit = OUT OF PLACE

**IMPORTANT**: In "specific_concerns", explicitly identify tracks that should be REMOVED from the playlist.
Use exact format: "Track Name by Artist Name feels out of place because..."

Respond in JSON format:
{{
  "quality_score": <float 0-1>,
  "meets_expectations": <boolean>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "issues": ["<issue 1>", "<issue 2>"],
  "specific_concerns": ["<exact track name> by <artist name> feels out of place because..."],
  "reasoning": "<brief explanation>"
}}"""