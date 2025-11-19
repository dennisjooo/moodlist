"""Prompts for LLM-based seed selection."""


def get_seed_selection_prompt(
    mood_prompt: str,
    features_summary: list,
    candidate_count: int,
    ideal_count: int,
    candidate_tracks: list,
) -> str:
    """Get the prompt for LLM-based seed selection.

    Args:
        mood_prompt: User's mood description
        features_summary: List of target feature descriptions
        candidate_count: Number of candidate tracks
        ideal_count: Ideal number of seeds to select
        candidate_tracks: List of candidate track descriptions

    Returns:
        Formatted prompt string
    """
    return f"""You are a music curator selecting seed tracks for a mood-based playlist.

**User's Mood**: "{mood_prompt}"

**Target Audio Features**: {", ".join(features_summary)}

**Task**: From the provided {candidate_count} candidate tracks (already ranked by how well they match the mood), select {ideal_count} tracks that would make the best seeds for generating a cohesive playlist.

Consider:
1. The tracks are already scored and ordered by match quality
2. Select tracks that exemplify the mood
3. Prefer variety in the seeds (don't pick all similar tracks)
4. Balance between strong mood matches and diversity

**Candidates** (ranked by score):
{chr(10).join([f"{i + 1}. Track {track_id[:8]}..." for i, track_id in enumerate(candidate_tracks)])}

Respond in JSON format:
{{
  "selected_indices": [1, 2, 3, ...],
  "reasoning": "Brief explanation of selection strategy"
}}

Select approximately {ideal_count} indices from the list above."""
