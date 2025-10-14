"""Prompt for playlist description generation."""


def get_playlist_description_prompt(mood_prompt: str, track_count: int) -> str:
    """Get the prompt for generating playlist descriptions.

    Args:
        mood_prompt: User's mood description
        track_count: Number of tracks in the playlist

    Returns:
        Prompt string for playlist description
    """
    return f"""
    Create a creative and engaging playlist description based on this mood: "{mood_prompt}"

    The playlist contains {track_count} tracks that match this mood perfectly.

    Guidelines:
    - Keep it under 200 characters total
    - Make it emotionally resonant and appealing
    - End with exactly: "{track_count} tracks curated with love by MoodList"
    - Focus on the feeling and atmosphere the music creates
    - Be specific to the mood but keep it concise

    Return only the description text, nothing else.
    """