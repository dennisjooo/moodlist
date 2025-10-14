def get_artist_filtering_prompt(mood_prompt: str, mood_interpretation: str, artists_summary: str) -> str:
    """Get the prompt for filtering artists based on mood compatibility."""
    return f"""You are a music curator selecting artists that match a specific mood.

**User's Mood**: "{mood_prompt}"

**Mood Analysis**: {mood_interpretation}

**Available Artists**:
{artists_summary}

**Task**: Select 12-20 artists from the list that best match this mood for MAXIMUM DIVERSITY. Consider:
1. Genre compatibility with the mood
2. Artist style and vibe
3. IMPORTANT: Mix of popular and lesser-known artists for variety
4. Overall cohesion with the requested mood
5. Prefer MORE artists over fewer for playlist diversity

Respond in JSON format:
{{
  "selected_artist_indices": [1, 3, 5, ...],
  "reasoning": "Brief explanation of why these artists fit the mood"
}}

Select artist indices (numbers from the list above). Aim for 12-20 artists for best diversity."""