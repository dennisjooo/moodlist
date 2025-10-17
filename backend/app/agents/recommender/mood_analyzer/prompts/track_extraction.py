"""Prompt for extracting user-mentioned tracks from mood prompts."""


def get_track_extraction_prompt(mood_prompt: str, artist_recommendations: list[str]) -> str:
    """Get the prompt for extracting specific tracks mentioned by the user.
    
    Args:
        mood_prompt: User's original mood description
        artist_recommendations: List of artist names from mood analysis
        
    Returns:
        Prompt string for track extraction
    """
    artists_context = ', '.join(artist_recommendations) if artist_recommendations else 'None'
    
    return f"""Analyze this user's music request and extract any SPECIFIC TRACK NAMES they mentioned.

User's request: "{mood_prompt}"

Context - Artists detected in the request: {artists_context}

Task: Identify any specific song/track titles the user mentioned. Look for patterns like:
- "especially [track name]"
- "like [track name]"
- "songs like [track name]"
- "[track name] by [artist]"
- Any other mentions of specific songs

Respond in JSON format:
{{
  "mentioned_tracks": [
    {{"track_name": "Track Title", "artist_name": "Artist Name"}},
    {{"track_name": "Another Track", "artist_name": "Artist Name"}}
  ],
  "reasoning": "Brief explanation of what tracks you found"
}}

If no specific tracks are mentioned, return an empty array for mentioned_tracks.
Only include tracks that are clearly mentioned by name, not just genres or moods."""

