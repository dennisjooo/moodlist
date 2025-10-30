"""Prompt templates for track energy analysis."""
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

