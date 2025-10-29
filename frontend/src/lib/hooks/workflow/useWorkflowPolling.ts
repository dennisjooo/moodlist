'use client';

import { useEffect, useRef } from 'react';
import { pollingManager } from '@/lib/pollingManager';
import { workflowAPI } from '@/lib/api/workflow';
import type { WorkflowStatus, WorkflowResults } from '@/lib/api/workflow';
import { logger } from '@/lib/utils/logger';

interface PollingCallbacks {
    onStatus?: (status: WorkflowStatus) => void | Promise<void>;
    onError?: (error: Error) => void;
    onAwaitingInput?: () => void;
    onTerminal?: (status: WorkflowStatus, results: WorkflowResults | null) => void | Promise<void>;
}

interface UseWorkflowPollingOptions {
    enabled?: boolean;
    callbacks?: PollingCallbacks;
}

/**
 * Custom hook to manage workflow polling lifecycle
 * Automatically starts/stops polling based on session ID and enabled flag
 */
export function useWorkflowPolling(
    sessionId: string | null,
    status: WorkflowStatus['status'] | null,
    options: UseWorkflowPollingOptions = {}
) {
    const { enabled = true, callbacks = {} } = options;
    const callbacksRef = useRef(callbacks);

    // Keep callbacks ref up to date
    useEffect(() => {
        callbacksRef.current = callbacks;
    }, [callbacks]);

    useEffect(() => {
        // Don't poll if no session or disabled
        if (!sessionId || !enabled) {
            return;
        }

        // Check if workflow is in a terminal state
        const isTerminalState = status === 'completed' || status === 'failed';
        if (isTerminalState) {
            logger.debug('Workflow in terminal state, stopping polling', {
                component: 'useWorkflowPolling',
                sessionId
            });
            pollingManager.stopPolling(sessionId);
            return;
        }

        const pollWorkflow = async () => {
            return await workflowAPI.getWorkflowStatus(sessionId);
        };

        const handleStatus = async (status: WorkflowStatus) => {
            // Notify status change
            if (callbacksRef.current.onStatus) {
                await callbacksRef.current.onStatus(status);
            }

            // If workflow reached terminal state, fetch results and stop polling
            const isTerminal = status.status === 'completed' || status.status === 'failed';

            if (isTerminal) {
                logger.debug('Terminal state detected, stopping polling', {
                    component: 'useWorkflowPolling',
                    sessionId
                });
                pollingManager.stopPolling(sessionId);

                // Fetch results when workflow completes
                let results = null;
                try {
                    logger.debug('Fetching results for completed workflow', {
                        component: 'useWorkflowPolling',
                        sessionId
                    });
                    results = await workflowAPI.getWorkflowResults(sessionId);
                } catch (e) {
                    logger.error('Failed to fetch results for completed workflow', e, {
                        component: 'useWorkflowPolling',
                        sessionId
                    });
                }

                // Notify terminal state with results
                if (callbacksRef.current.onTerminal) {
                    await callbacksRef.current.onTerminal(status, results);
                }

                logger.info('Terminal state set with results, polling stopped', {
                    component: 'useWorkflowPolling',
                    sessionId
                });
            }
        };

        const handleError = (error: Error) => {
            logger.error('Workflow polling error', error, {
                component: 'useWorkflowPolling',
                sessionId
            });
            if (callbacksRef.current.onError) {
                callbacksRef.current.onError(error);
            }
        };

        const handleAwaitingInput = () => {
            logger.debug('Workflow awaiting user input', {
                component: 'useWorkflowPolling',
                sessionId
            });
            if (callbacksRef.current.onAwaitingInput) {
                callbacksRef.current.onAwaitingInput();
            }
        };

        logger.debug('Starting polling', {
            component: 'useWorkflowPolling',
            sessionId,
            status
        });

        pollingManager.startPolling(
            sessionId,
            pollWorkflow,
            {
                onStatus: handleStatus,
                onError: handleError,
                onAwaitingInput: handleAwaitingInput,
            }
        );

        logger.debug('Polling started', {
            component: 'useWorkflowPolling',
            sessionId
        });

        return () => {
            logger.debug('Cleanup: stopping polling', {
                component: 'useWorkflowPolling',
                sessionId
            });
            pollingManager.stopPolling(sessionId);
        };
    }, [sessionId, status, enabled]);
}

