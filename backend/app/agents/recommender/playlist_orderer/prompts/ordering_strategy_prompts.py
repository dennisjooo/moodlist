"""Prompt templates for determining playlist ordering strategy."""

import json
from typing import Any, Dict, List


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

**CRITICAL REQUIREMENTS**: 
1. You MUST use EXACTLY these 6 phase names (no variations, no custom names):
   - "opening" (first tracks that set the tone)
   - "build" (building energy/momentum)
   - "mid" (maintaining established energy)
   - "high" (peak energy moments)
   - "descent" (wind-down from peak)
   - "closure" (final resolution)

2. You MUST include ALL 6 phases in your phase_distribution, even if some have 0 tracks

3. DO NOT invent custom phase names like "low_mid_exploration" or "mid_point_warmth"
   - Use "mid" for any middle/exploration sections
   - Use "build" for any building sections
   - Use "descent" for any returning/wind-down sections

4. The sum of all phase counts MUST equal the total track count

Examples:
- Classic Build: {"opening": 2, "build": 5, "mid": 8, "high": 7, "descent": 4, "closure": 2}
- Chill Journey: {"opening": 3, "build": 4, "mid": 6, "high": 0, "descent": 4, "closure": 3}
- Ambient Flow: {"opening": 2, "build": 0, "mid": 12, "high": 0, "descent": 0, "closure": 2}

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
    user_mentioned_count: int,
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
{"... and more tracks" if len(track_analyses) > 10 else ""}

User Mentioned Tracks: {user_mentioned_count} tracks

**IMPORTANT**: 
- Your phase_distribution MUST include all 6 phases: opening, build, mid, high, descent, closure
- The sum of all phase track counts MUST equal {track_count}
- You can set phases to 0 if they don't fit the mood, but include them in the response

Provide an ordering strategy that creates the best listening experience."""
