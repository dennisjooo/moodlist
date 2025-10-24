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
    
    return f"""Analyze this user's music request and extract any SPECIFIC TRACK NAMES they explicitly mentioned.

User's request: "{mood_prompt}"

Context - Artists detected in the request: {artists_context}

Task: Identify any specific song/track titles the user mentioned BY NAME. Look for these patterns:

EXPLICIT TRACK MENTIONS (these are what we want):
- "Things like [Track Name] by [Artist]" → Extract: Track Name, Artist
- "[Track Name] by [Artist]" → Extract: Track Name, Artist
- "especially [Track Name]" → Extract: Track Name (use first artist from context)
- "like [Track Name]" → Extract: Track Name
- "songs like [Track Name]" → Extract: Track Name
- "tracks like [Track Name]" → Extract: Track Name

Examples:
- "Things like Escape Plan by Travis Scott" → {{"track_name": "Escape Plan", "artist_name": "Travis Scott"}}
- "songs like Sicko Mode" → {{"track_name": "Sicko Mode", "artist_name": "Travis Scott"}} (if Travis Scott is in context)
- "music like All The Stars by Kendrick Lamar" → {{"track_name": "All The Stars", "artist_name": "Kendrick Lamar"}}

IMPORTANT: 
- Only extract ACTUAL track names, not artist names alone
- "like Travis Scott" is NOT a track mention (it's an artist style reference)
- "Travis Scott vibes" is NOT a track mention
- Be precise with track names - extract the exact name mentioned

Respond in JSON format:
{{
  "mentioned_tracks": [
    {{"track_name": "Escape Plan", "artist_name": "Travis Scott"}},
    {{"track_name": "Another Track", "artist_name": "Artist Name"}}
  ],
  "reasoning": "Brief explanation of what tracks you found and why"
}}

If no specific tracks are mentioned BY NAME, return an empty array for mentioned_tracks.
Only include tracks that are clearly mentioned by their actual track name, not just genres, moods, or artist names."""

