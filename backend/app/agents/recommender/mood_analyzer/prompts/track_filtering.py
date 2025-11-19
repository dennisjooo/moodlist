"""Prompts for LLM-based track and artist filtering."""

from typing import Dict, Any, List


def get_artist_validation_prompt(
    artist_info: Dict[str, Any], mood_prompt: str, mood_analysis: Dict[str, Any]
) -> str:
    """Get prompt for validating if an artist matches the mood request.

    Args:
        artist_info: Artist information including name, genres, popularity
        mood_prompt: User's original mood prompt
        mood_analysis: Full mood analysis context

    Returns:
        Prompt string for artist validation
    """
    artist_name = artist_info.get("name", "Unknown")
    genres = artist_info.get("genres", [])
    genres_str = ", ".join(genres) if genres else "No genres listed"
    popularity = artist_info.get("popularity", 0)

    mood_interpretation = mood_analysis.get("mood_interpretation", "")
    target_genres = ", ".join(mood_analysis.get("genre_keywords", []))
    recommended_artists = ", ".join(
        mood_analysis.get("artist_recommendations", [])[:10]
    )
    preferred_regions = ", ".join(mood_analysis.get("preferred_regions", []))
    excluded_regions = ", ".join(mood_analysis.get("excluded_regions", []))
    excluded_themes = ", ".join(mood_analysis.get("excluded_themes", []))

    return f"""Validate whether this artist is appropriate for the user's music request.

User's mood request: "{mood_prompt}"

Mood interpretation: {mood_interpretation}
Target genres: {target_genres}
Reference artists: {recommended_artists}
Preferred regions: {preferred_regions}
Excluded regions: {excluded_regions}
Excluded themes: {excluded_themes}

Artist to validate:
- Name: {artist_name}
- Genres: {genres_str}
- Popularity: {popularity}

Task: Determine if this artist fits the mood request or is a cultural/genre/theme mismatch.

Red flags to watch for:
1. **Regional Mismatch**: Artist from wrong region (e.g., Indonesian artist for "French funk")
2. **Genre Drift**: Artist genres don't align (e.g., "disco polo" for "nu-disco")
3. **Language Incompatibility**: Non-Western artist when Western music requested
4. **Style Mismatch**: Artist's style doesn't fit the vibe
5. **Theme Mismatch**: Artist primarily known for excluded themes (e.g., Christmas music when excluded)

Green flags:
1. Genres overlap with target genres
2. Artist from culturally appropriate region
3. Similar to reference artists
4. Fits the mood interpretation

Respond in JSON format:
{{
  "is_valid": true,
  "confidence": 0.9,
  "reasoning": "Artist genres align with nu-disco/French house, European artist fits French funk aesthetic",
  "match_score": 0.85,
  "concerns": []
}}

Set `is_valid` to false if there's a clear mismatch. Add specific concerns if needed."""


def get_batch_track_filter_prompt(
    tracks: List[Dict[str, Any]], mood_prompt: str, mood_analysis: Dict[str, Any]
) -> str:
    """Get prompt for batch filtering tracks for cultural/linguistic relevance.

    Args:
        tracks: List of track dictionaries to filter
        mood_prompt: User's original mood prompt
        mood_analysis: Full mood analysis context

    Returns:
        Prompt string for batch track filtering
    """
    mood_interpretation = mood_analysis.get("mood_interpretation", "")
    genre_keywords = ", ".join(mood_analysis.get("genre_keywords", []))
    preferred_regions = ", ".join(mood_analysis.get("preferred_regions", []))
    excluded_regions = ", ".join(mood_analysis.get("excluded_regions", []))
    excluded_themes = ", ".join(mood_analysis.get("excluded_themes", []))

    # Format tracks
    tracks_info = []
    for i, track in enumerate(tracks[:20]):  # Limit to 20 for prompt size
        artists = [a.get("name", "") for a in track.get("artists", [])]
        artist_str = ", ".join(artists) if artists else "Unknown"
        tracks_info.append(f"{i + 1}. '{track.get('name', 'Unknown')}' by {artist_str}")

    tracks_context = "\n".join(tracks_info)

    return f"""Filter these tracks for cultural and linguistic relevance to the user's request.

User's mood request: "{mood_prompt}"

Mood interpretation: {mood_interpretation}
Target genres: {genre_keywords}
Preferred regions: {preferred_regions}
Excluded regions: {excluded_regions}
Excluded themes: {excluded_themes}

Tracks to filter:
{tracks_context}

Task: Identify tracks that are cultural/linguistic/thematic mismatches.

Common mismatches to flag:
- Indonesian/Malaysian tracks when requesting Western genres
- Thai tracks when requesting European/American music
- Polish/Eastern European tracks when requesting French/Nu-Disco
- K-pop when requesting non-Asian genres (unless K-pop requested)
- Latin American tracks when requesting European electronic music
- Holiday/Christmas songs when not requesting holiday music (e.g., "O Holy Night", "Jingle Bells", "Silent Night")
- Religious/worship songs when requesting secular music
- Children's songs when not requesting kids music
- Comedy/parody tracks when requesting serious music

Tracks should pass if:
- Language/region matches the mood request
- Western/English tracks for ambiguous requests
- Culturally appropriate for the specified genre
- No thematic conflicts with excluded themes (check track titles for obvious indicators)

Respond in JSON format:
{{
  "relevant_tracks": [0, 2, 3, 5],
  "filtered_out": [
    {{
      "track_index": 1,
      "reason": "Indonesian pop, doesn't match French funk aesthetic"
    }},
    {{
      "track_index": 4,
      "reason": "Polish disco polo, incompatible with nu-disco request"
    }}
  ],
  "summary": "Filtered 2 tracks due to language/regional mismatch"
}}

Return indices of tracks that should be KEPT in `relevant_tracks`."""
