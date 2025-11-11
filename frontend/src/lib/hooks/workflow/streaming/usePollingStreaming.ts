/**
 * Polling fallback handler for workflow status updates.
 */

import { pollingManager } from '@/lib/pollingManager';
import { workflowAPI } from '@/lib/api/workflow';
import { logger } from '@/lib/utils/logger';
import { isTerminalStatus } from '@/lib/utils/workflow';
import type { WorkflowStatus } from '@/lib/api/workflow';
import type { StreamingCallbacks } from './streamingCallbacks';

export function usePollingStreaming(
    sessionId: string,
    callbacks: StreamingCallbacks,
    terminalHandledRef: React.RefObject<boolean>
): () => void {
    logger.info('Starting polling fallback', {
        component: 'usePollingStreaming',
        sessionId
    });

    const pollWorkflow = async () => {
        return await workflowAPI.getWorkflowStatus(sessionId);
    };

    const handleStatus = async (status: WorkflowStatus) => {
        // Notify status change
        if (callbacks.onStatus) {
            await callbacks.onStatus(status);
        }

        // If workflow reached terminal state, fetch results and stop polling
        const isTerminal = isTerminalStatus(status.status);

        if (isTerminal) {
            logger.debug('Terminal state detected, stopping polling', {
                component: 'usePollingStreaming',
                sessionId
            });
            pollingManager.stopPolling(sessionId);

            // Fetch results when workflow completes
            let results = null;
            try {
                logger.debug('Fetching results for completed workflow', {
                    component: 'usePollingStreaming',
                    sessionId
                });
                results = await workflowAPI.getWorkflowResults(sessionId);
            } catch (e) {
                logger.error('Failed to fetch results for completed workflow', e, {
                    component: 'usePollingStreaming',
                    sessionId
                });
            }

            // Notify terminal state with results
            if (callbacks.onTerminal) {
                await callbacks.onTerminal(status, results);
            }

            logger.info('Terminal state set with results, polling stopped', {
                component: 'usePollingStreaming',
                sessionId
            });
        }
    };

    const handleError = (error: Error) => {
        logger.error('Workflow polling error', error, {
            component: 'usePollingStreaming',
            sessionId
        });
        if (callbacks.onError) {
            callbacks.onError(error);
        }
    };

    const handleAwaitingInput = () => {
        logger.debug('Workflow awaiting user input', {
            component: 'usePollingStreaming',
            sessionId
        });
        if (callbacks.onAwaitingInput) {
            callbacks.onAwaitingInput();
        }
    };

    pollingManager.startPolling(
        sessionId,
        pollWorkflow,
        {
            onStatus: handleStatus,
            onError: handleError,
            onAwaitingInput: handleAwaitingInput,
        }
    );

    // Return cleanup function
    return () => {
        logger.debug('Cleanup: stopping polling', {
            component: 'usePollingStreaming',
            sessionId
        });
        pollingManager.stopPolling(sessionId);
    };
}

