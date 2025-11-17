/**
 * Configuration for workflow stages with weights used for progress calculation.
 * Weights are based on observed average time spent in each stage:
 * - Analyzing mood: ~15s (12%)
 * - Gathering seeds: ~45s (35%)
 * - Generating recommendations: ~30s (24%)
 * - Evaluating quality: ~10s (8%)
 * - Optimizing: ~5s (4%)
 * - Ordering: ~7s (6%)
 * - Creating: ~8s (6%)
 * - Completed: ~5s (5%)
 */
export interface WorkflowStage {
    key: string;
    label: string;
    weight: number;
}

export const WORKFLOW_STAGES: readonly WorkflowStage[] = [
    { key: 'analyzing_mood', label: 'Analyzing mood', weight: 0.12 },
    { key: 'gathering_seeds', label: 'Finding seeds', weight: 0.35 },
    { key: 'generating_recommendations', label: 'Generating playlist', weight: 0.24 },
    { key: 'evaluating_quality', label: 'Evaluating', weight: 0.08 },
    { key: 'optimizing_recommendations', label: 'Optimizing', weight: 0.04 },
    { key: 'ordering_playlist', label: 'Ordering tracks', weight: 0.06 },
    { key: 'creating_playlist', label: 'Creating playlist', weight: 0.06 },
    { key: 'completed', label: 'Complete', weight: 0.05 },
] as const;

export const WORKFLOW_STAGE_CONFIG = Object.freeze({
    stages: WORKFLOW_STAGES,
    totalWeight: WORKFLOW_STAGES.reduce((acc, stage) => acc + stage.weight, 0),
});

interface StageInfo {
    stage: WorkflowStage;
    index: number;
    cumulativeWeight: number;
    weight: number;
}

/**
 * Find the matching stage for a given status string.
 * Returns the stage info including cumulative progress up to that stage.
 */
export function resolveStageForStatus(status: string | null): StageInfo {
    if (!status) {
        return {
            stage: WORKFLOW_STAGES[0],
            index: 0,
            cumulativeWeight: 0,
            weight: WORKFLOW_STAGES[0].weight,
        };
    }

    let cumulativeWeight = 0;
    for (let i = 0; i < WORKFLOW_STAGES.length; i++) {
        const stage = WORKFLOW_STAGES[i];
        if (status.includes(stage.key)) {
            return {
                stage,
                index: i,
                cumulativeWeight,
                weight: stage.weight,
            };
        }
        cumulativeWeight += stage.weight;
    }

    // Default to first stage if no match
    return {
        stage: WORKFLOW_STAGES[0],
        index: 0,
        cumulativeWeight: 0,
        weight: WORKFLOW_STAGES[0].weight,
    };
}
