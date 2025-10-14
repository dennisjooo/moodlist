"""Prompt for playlist naming."""


def get_playlist_naming_prompt(mood_prompt: str, track_count: int) -> str:
    """Get the prompt for generating playlist names.

    Args:
        mood_prompt: User's mood description
        track_count: Number of tracks in the playlist

    Returns:
        Prompt string for playlist naming
    """
    return f"""
    Create a creative and appealing playlist name based on this mood description: "{mood_prompt}"

    The playlist contains {track_count} tracks that match this mood.

    Guidelines:
    - Keep it under 100 characters
    - Make it catchy and relevant to the mood
    - Avoid generic names like "My Playlist"
    - Consider the energy and emotion of the mood

    Consider it as a unified title, no subtitle.

    Return only the playlist name, nothing else.
    """