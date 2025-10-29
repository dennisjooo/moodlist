"""Prompt templates for playlist ordering and energy flow analysis."""
import json
from typing import Any, Dict, List


def get_track_energy_analysis_system_prompt() -> str:
    """Get the system prompt for analyzing track energy characteristics."""
    return """You are an expert music curator specializing in playlist flow and energy dynamics.

Your task is to analyze a list of tracks and determine their energy characteristics for optimal playlist ordering.

For each track, analyze:
1. **Energy Level** (0-100): Overall intensity, tempo, and vigor
   - 0-20: Very calm, ambient, meditative
   - 21-40: Relaxed, mellow, low-key
   - 41-60: Moderate, balanced, conversational
   - 61-80: Energetic, upbeat, engaging
   - 81-100: High-intensity, explosive, peak energy

2. **Momentum** (0-100): How much the track drives forward
   - 0-20: Static, atmospheric, no drive
   - 21-40: Gentle movement, slow build
   - 41-60: Steady progression, consistent pace
   - 61-80: Strong drive, builds tension
   - 81-100: Relentless forward motion, climactic

3. **Emotional Intensity** (0-100): Depth of emotional expression
   - 0-20: Subtle, understated, background
   - 21-40: Gentle emotion, intimate
   - 41-60: Clear emotional expression
   - 61-80: Powerful emotion, impactful
   - 81-100: Overwhelming, cathartic, peak emotion

4. **Opening Potential** (0-100): Suitability as a playlist opener
   - High scores: Welcoming, sets the tone, draws listener in
   - Low scores: Too abrupt, needs context, better for later

5. **Closing Potential** (0-100): Suitability as a playlist closer
   - High scores: Resolves tension, satisfying conclusion, memorable ending
   - Low scores: Leaves energy unresolved, feels incomplete

6. **Peak Potential** (0-100): Suitability as a playlist climax
   - High scores: Maximum impact, emotional/energy peak, pivotal moment
   - Low scores: Not memorable enough for peak placement

Consider audio features like:
- Tempo (BPM)
- Energy (from Spotify features)
- Danceability
- Valence (positivity)
- Loudness
- Instrumentalness
- Speechiness

Respond in JSON format:
{
  "track_analyses": [
    {
      "track_id": "spotify_track_id",
      "track_name": "Track Name - Artist",
      "energy_level": 75,
      "momentum": 80,
      "emotional_intensity": 70,
      "opening_potential": 60,
      "closing_potential": 40,
      "peak_potential": 85,
      "phase_assignment": "high",
      "reasoning": "Brief explanation of the energy profile"
    }
  ]
}

Phase assignments should be one of:
- "opening": Best for starting the playlist (first 2-3 tracks)
- "build": Building energy and momentum (next 20-30%)
- "mid": Maintaining established energy (middle 30-40%)
- "high": Peak energy moments (next 20-30%)
- "descent": Gradual wind-down from peak (next 10-15%)
- "closure": Final resolution and landing (last 1-2 tracks)
"""


def get_track_energy_analysis_user_prompt(
    mood_prompt: str,
    tracks_info: List[Dict[str, Any]]
) -> str:
    """Get the user prompt for track energy analysis.
    
    Args:
        mood_prompt: User's mood description
        tracks_info: List of track information dictionaries
        
    Returns:
        Formatted user prompt
    """
    return f"""Analyze the energy characteristics of these tracks for playlist ordering:

Mood Context: {mood_prompt}

Tracks to analyze:
{json.dumps(tracks_info, indent=2)}

Provide energy analysis for each track to determine optimal ordering."""


def get_ordering_strategy_system_prompt() -> str:
    """Get the system prompt for determining the overall ordering strategy."""
    return """You are an expert DJ and playlist curator specializing in creating cohesive listening experiences.

Based on the mood and energy profile of a playlist, determine the optimal ordering strategy to create a satisfying energy arc.

Common energy arc patterns:

1. **Classic Build** (Beginning → Mid → High → Descent → Closure)
   - Start calm/moderate
   - Gradually build energy
   - Peak in the middle-to-late section
   - Gentle wind-down
   - Satisfying closure
   - Best for: workout playlists, party playlists, storytelling arcs

2. **Immediate Impact** (High → Mid-High → High → Descent → Closure)
   - Start with high energy to grab attention
   - Maintain elevated energy
   - Peak moments throughout
   - Strong ending
   - Best for: hype playlists, pump-up music, energetic moods

3. **Chill Journey** (Low → Low-Mid → Mid → Low-Mid → Low)
   - Start ambient/calm
   - Gentle exploration of energy
   - Never too intense
   - Return to calm
   - Best for: study music, relaxation, ambient playlists

4. **Emotional Rollercoaster** (Mid → High → Low → High → Mid)
   - Dynamic energy changes
   - Multiple peaks and valleys
   - Keeps listener engaged through contrast
   - Best for: emotional playlists, diverse moods, long listening sessions

5. **Sustained Energy** (High → High → High → High → High)
   - Consistent high energy throughout
   - Minimal variation
   - Relentless drive
   - Best for: workout playlists, party sets, high-energy moods

6. **Ambient Flow** (Low → Low → Low → Low → Low)
   - Consistent calm/low energy
   - Gentle variations only
   - Maintains atmosphere
   - Best for: sleep, meditation, background music

Analyze the mood prompt, track energy profiles, and determine:
1. Which energy arc pattern best fits this playlist
2. How to assign tracks to phases
3. Any special considerations (e.g., user-mentioned tracks should be prioritized)
4. Optimal ordering within each phase (smooth transitions)

Respond in JSON format:
{
  "strategy": "classic_build | immediate_impact | chill_journey | emotional_rollercoaster | sustained_energy | ambient_flow",
  "reasoning": "Why this strategy fits the mood and tracks",
  "phase_distribution": {
    "opening": 2,
    "build": 5,
    "mid": 8,
    "high": 7,
    "descent": 4,
    "closure": 2
  },
  "special_considerations": [
    "User mentioned Track X - place in high energy phase",
    "Strong opener available - use Track Y",
    "Natural closer - Track Z has perfect resolution"
  ],
  "transition_notes": "How to handle transitions between phases"
}
"""


def get_ordering_strategy_user_prompt(
    mood_prompt: str,
    track_count: int,
    avg_energy: float,
    max_energy: float,
    min_energy: float,
    energy_range: float,
    track_analyses: List[Dict[str, Any]],
    user_mentioned_count: int
) -> str:
    """Get the user prompt for ordering strategy determination.
    
    Args:
        mood_prompt: User's mood description
        track_count: Number of tracks
        avg_energy: Average energy level
        max_energy: Maximum energy level
        min_energy: Minimum energy level
        energy_range: Range of energy levels
        track_analyses: List of track analyses
        user_mentioned_count: Number of user-mentioned tracks
        
    Returns:
        Formatted user prompt
    """
    return f"""Determine the optimal ordering strategy for this playlist:

Mood Context: {mood_prompt}

Track Count: {track_count}

Energy Statistics:
- Average Energy: {avg_energy:.1f}
- Energy Range: {energy_range:.1f} (min: {min_energy:.1f}, max: {max_energy:.1f})

Track Analyses Summary:
{json.dumps(track_analyses[:10], indent=2)}
{'... and more tracks' if len(track_analyses) > 10 else ''}

User Mentioned Tracks: {user_mentioned_count} tracks

Provide an ordering strategy that creates the best listening experience."""


