import type { WorkflowStatus } from '../api/workflow';

/**
 * Defines the workflow stage progression order to ensure monotonic progress
 * and prevent backwards status updates
 */
export const WORKFLOW_STAGE_ORDER = [
    'started',
    'pending',
    'analyzing_mood',
    'gathering_seeds',
    'generating_recommendations',
    'evaluating_quality',
    'optimizing_recommendations',
    'creating_playlist',
    'completed',
    'failed'
] as const;

/**
 * Gets the stage index for a given workflow status
 */
export function getWorkflowStageIndex(status: string | null): number {
    if (!status) return -1;
    return WORKFLOW_STAGE_ORDER.findIndex(stage => status.includes(stage));
}

/**
 * Determines if a status update should be accepted based on workflow progress rules
 */
export function shouldAcceptStatusUpdate(
    prevStatus: string | null,
    newStatus: string,
    hasNewError: boolean = false
): boolean {
    // Always accept if no previous status
    if (!prevStatus) return true;

    // Always accept terminal states
    if (newStatus === 'completed' || newStatus === 'failed') return true;

    // Always accept if there's a new error
    if (hasNewError) return true;

    const prevIndex = getWorkflowStageIndex(prevStatus);
    const newIndex = getWorkflowStageIndex(newStatus);

    // Accept if status is unknown (not in our defined stages)
    // This handles sub-steps and detailed status updates
    if (newIndex === -1) return true;

    // Accept if moving forward in the workflow
    if (newIndex > prevIndex) return true;

    // Accept if we're at the same stage (sub-steps within a stage)
    if (newIndex === prevIndex) return true;

    // Reject only if moving backwards
    return false;
}

/**
 * Checks if a workflow status is in a terminal state
 */
export function isTerminalStatus(status: string | null): boolean {
    return status === 'completed' || status === 'failed';
}

/**
 * Checks if a workflow should stream updates (only on create pages)
 */
export function shouldStreamWorkflow(pathname: string | null, sessionId: string | null): boolean {
    const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    return Boolean(sessionId && isCreatePage);
}
