"""Prompt templates for intent analysis."""


def get_intent_analysis_prompt(mood_prompt: str) -> str:
    """Get the prompt for analyzing user intent.
    
    Args:
        mood_prompt: User's mood/playlist request
        
    Returns:
        Prompt string for LLM intent analysis
    """
    return f"""You are an expert music recommendation system analyzing user intent to build better playlists.

**User Request**: "{mood_prompt}"

**Your Task**: Analyze this request to understand what the user really wants. Extract:

1. **Intent Type** - What kind of playlist does the user want?
   - "artist_focus": User wants music from a specific artist or few artists (e.g., "Travis Scott playlist", "things like Travis Scott")
   - "genre_exploration": User wants to explore a genre with variety (e.g., "French funk", "trap bangers")
   - "mood_variety": User wants diverse tracks matching a mood (e.g., "happy upbeat songs", "chill study music")
   - "specific_track_similar": User mentioned specific tracks and wants similar ones

2. **User-Mentioned Tracks** - Extract tracks explicitly mentioned:
   - Track name (required)
   - Artist name (required)
   - Priority: "high" if user said "like this" or "similar to", "medium" otherwise
   
3. **User-Mentioned Artists** - Extract artists explicitly mentioned (as array of strings)

4. **Primary Genre** - What is the main genre? (e.g., "trap", "hip hop", "indie rock", "electronic", "pop")
   - Use null if genre is unclear

5. **Genre Strictness** (0.0-1.0) - How strict should genre matching be?
   - 0.9-1.0: Very strict (user mentioned specific genre/artist, wants only that style)
   - 0.6-0.8: Moderate (user wants similar vibes but some variety ok)
   - 0.3-0.5: Loose (user wants mood-based variety)

6. **Language Preferences** - Which languages/regions does the user want?
   - Use ["english"] if not specified
   - Examples: ["english"], ["spanish"], ["korean"], ["any"]

7. **Exclude Regions** - Which regions should be excluded based on context?
   - Examples: ["southeast_asian"] if user wants Western trap (not Indonesian pop)
   - Examples: ["latin_american"] if user wants English-only
   - Use [] (empty) if no obvious exclusions

8. **Allow Obscure Artists** (true/false) - Based on user's intent:
   - false: User mentioned mainstream artists (Travis Scott, Drake, etc.)
   - true: User wants underground/indie/niche artists

9. **Quality Threshold** (0.0-1.0) - How confident should recommendations be?
   - 0.8-1.0: User mentioned specific tracks/artists (high bar)
   - 0.6-0.7: User mentioned genre (moderate bar)
   - 0.4-0.5: User gave vague mood (lower bar, more exploration)

**Examples**:

Example 1: "Things like Escape Plan by Travis Scott"
→ intent_type: "specific_track_similar"
→ user_mentioned_tracks: [{{"track_name": "Escape Plan", "artist_name": "Travis Scott", "priority": "high"}}]
→ user_mentioned_artists: ["Travis Scott"]
→ primary_genre: "trap"
→ genre_strictness: 0.9
→ exclude_regions: ["southeast_asian"]
→ allow_obscure_artists: false
→ quality_threshold: 0.7

Example 2: "Give me a Travis Scott playlist"
→ intent_type: "artist_focus"
→ user_mentioned_artists: ["Travis Scott"]
→ primary_genre: "trap"
→ genre_strictness: 0.7
→ allow_obscure_artists: false

Example 3: "French funk vibes for a party"
→ intent_type: "genre_exploration"
→ primary_genre: "funk"
→ language_preferences: ["french"]
→ genre_strictness: 0.6
→ allow_obscure_artists: true

**Respond in JSON format**:
{{{{
  "intent_type": "<artist_focus|genre_exploration|mood_variety|specific_track_similar>",
  "user_mentioned_tracks": [
    {{"track_name": "...", "artist_name": "...", "priority": "high|medium"}}
  ],
  "user_mentioned_artists": ["artist1", "artist2"],
  "primary_genre": "<genre name or null>",
  "genre_strictness": 0.0-1.0,
  "language_preferences": ["english"],
  "exclude_regions": ["region1", "region2"],
  "allow_obscure_artists": true/false,
  "quality_threshold": 0.0-1.0,
  "reasoning": "<1-2 sentence explanation of your analysis>"
}}}}

Now analyze: "{mood_prompt}"
"""

