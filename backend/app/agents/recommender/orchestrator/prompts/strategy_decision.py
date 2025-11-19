"""Prompt templates for strategy decision."""


def get_strategy_decision_prompt(
    mood_prompt: str,
    quality_evaluation: dict,
    issues_summary: str,
    llm_assessment_reasoning: str,
    target_count: int,
    iteration: int,
) -> str:
    """Get the prompt for deciding improvement strategies.

    Args:
        mood_prompt: User's original mood request
        quality_evaluation: Quality evaluation results
        issues_summary: Summary of issues found
        llm_assessment_reasoning: LLM's reasoning about quality
        target_count: Target number of tracks
        iteration: Current iteration number

    Returns:
        Prompt string for LLM strategy decision
    """
    return f"""You are a music recommendation system optimizer deciding how to improve a playlist.

**Current Situation**:
- Mood: "{mood_prompt}"
- Current: {quality_evaluation["recommendations_count"]} tracks
- Target: {target_count} tracks
- Cohesion Score: {quality_evaluation["cohesion_score"]:.2f}/1.0
- Overall Score: {quality_evaluation["overall_score"]:.2f}/1.0
- Outliers: {len(quality_evaluation["outlier_tracks"])} tracks
- Iteration: {iteration}/3

**Issues**:
{issues_summary or "No major issues detected"}

**LLM Assessment**: {llm_assessment_reasoning}

**Available Strategies** (can select multiple for compound approach):
1. "filter_and_replace" - Remove outlier tracks and generate replacements
2. "reseed_from_clean" - Use best current tracks as seeds for new generation
3. "adjust_feature_weights" - Make mood matching stricter
4. "generate_more" - Add more recommendations to reach target count

**Task**: Select 1-3 strategies that would best improve this playlist. Consider:
- Multiple strategies can work together (compound approach)
- Order matters (strategies execute sequentially)
- Balance between quality and maintaining sufficient recommendations

Respond in JSON format:
{{
  "strategies": ["<strategy1>", "<strategy2>"],
  "reasoning": "<why these strategies in this order>"
}}"""
