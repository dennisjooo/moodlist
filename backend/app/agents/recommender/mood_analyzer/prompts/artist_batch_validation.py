"""Prompt for batch artist validation and filtering."""

from typing import Any, Dict, List


def get_batch_artist_validation_prompt(
    artists: List[Dict[str, Any]], mood_prompt: str, mood_analysis: Dict[str, Any]
) -> str:
    """Get prompt for validating a batch of artists for cultural/genre relevance.

    Args:
        artists: List of artist candidates
        mood_prompt: User's original mood prompt
        mood_analysis: Full mood analysis context

    Returns:
        Prompt string for batch artist validation
    """
    mood_interpretation = mood_analysis.get("mood_interpretation", "")
    genre_keywords = ", ".join(mood_analysis.get("genre_keywords", []))
    preferred_regions = ", ".join(mood_analysis.get("preferred_regions", []))
    excluded_regions = ", ".join(mood_analysis.get("excluded_regions", []))
    recommended_artists = ", ".join(
        mood_analysis.get("artist_recommendations", [])[:10]
    )

    # Format artists
    artists_info = []
    for i, artist in enumerate(artists[:30]):  # Limit to 30 for prompt size
        genres = artist.get("genres", [])
        genres_str = ", ".join(genres[:5]) if genres else "No genres listed"
        popularity = artist.get("popularity", 0)
        artists_info.append(
            f"{i}. {artist.get('name', 'Unknown')} | Genres: {genres_str} | Popularity: {popularity}"
        )

    artists_context = "\n".join(artists_info)

    return f"""Evaluate which artists are culturally and genre-appropriate for the user's music request.

User's mood request: "{mood_prompt}"

Mood interpretation: {mood_interpretation}
Target genres: {genre_keywords}
Reference artists: {recommended_artists}
Preferred regions: {preferred_regions}
Excluded regions: {excluded_regions}

Artists to evaluate:
{artists_context}

Task: Identify which artists should be KEPT for this music request, and which should be filtered out.

Consider:
1. **Regional Fit (CRITICAL)**: Does the artist match the preferred_regions and avoid excluded_regions?
   - Check the artist's genres for regional indicators (e.g., "indonesian pop", "k-pop", "french rap")
   - ANY artist from an EXCLUDED REGION must be filtered out
   - Examples:
     * Indonesian/Malay/Southeast Asian artists (Tulus, Nadin Amizah, Hindia, Sal Priadi) → Filter if "Southeast Asian" in excluded_regions
     * Korean/K-pop artists → Filter if "East Asian" in excluded_regions
     * Latin/Spanish artists → Filter if "Latin American" in excluded_regions

2. **Genre Alignment**: Do the artist's genres match the requested mood/genres?

3. **Cultural Context**: Does the artist's origin/style fit the cultural aesthetic requested?
   - Example: For "French funk", Indonesian pop artists are a mismatch
   - Example: For "K-pop", Korean artists are appropriate

4. **Musical Style**: Does the artist's sound align with the mood interpretation?

**STRICT REGIONAL FILTERING RULES**:
- If excluded_regions is specified, ANY artist from those regions MUST be filtered
- Regional indicators in genres are definitive - if genre contains "indonesian", "malay", "k-pop", etc., treat it as that region
- Don't make exceptions for popular artists - regional filtering applies to everyone

Respond in JSON format:
{{
  "keep_artists": [0, 2, 5, 7, ...],
  "filtered_artists": [
    {{
      "index": 1,
      "name": "Artist Name",
      "reason": "Musical style doesn't align - Indonesian pop doesn't fit French funk aesthetic"
    }},
    {{
      "index": 3,
      "name": "Another Artist",
      "reason": "Genre mismatch - disco polo doesn't fit nu-disco request"
    }}
  ],
  "summary": "Kept 15 artists that match French/European funk aesthetic, filtered 8 with cultural/genre mismatches"
}}

Return indices (0-based) of artists to KEEP in the `keep_artists` array."""
