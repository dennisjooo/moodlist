/**
 * Common callback handlers for workflow streaming.
 * Shared logic for handling status updates, errors, and terminal states.
 */

import { workflowAPI } from '@/lib/api/workflow';
import type { WorkflowStatus, WorkflowResults } from '@/lib/api/workflow';
import { logger } from '@/lib/utils/logger';
import { isTerminalStatus } from '@/lib/utils/workflow';

export interface StreamingCallbacks {
    onStatus?: (status: WorkflowStatus) => void | Promise<void>;
    onError?: (error: Error) => void;
    onAwaitingInput?: () => void;
    onTerminal?: (status: WorkflowStatus, results: WorkflowResults | null) => void | Promise<void>;
}

export interface StreamingHandler {
    handleStatus: (status: WorkflowStatus) => Promise<void>;
    handleError: (error: Error) => void;
    handleComplete: () => Promise<void>;
    handleReconnect?: () => Promise<void>;
}

/**
 * Create streaming handlers with shared callback logic.
 */
export function createStreamingHandlers(
    sessionId: string,
    callbacks: StreamingCallbacks,
    terminalHandledRef: React.RefObject<boolean>
): StreamingHandler {
    const handleStatus = async (status: WorkflowStatus) => {
        // Notify status change
        if (callbacks.onStatus) {
            await callbacks.onStatus(status);
        }

        // Handle awaiting input state
        if (status.awaiting_input && callbacks.onAwaitingInput) {
            callbacks.onAwaitingInput();
        }

        // If workflow reached terminal state, fetch results
        const isTerminal = isTerminalStatus(status.status);

        if (isTerminal && !terminalHandledRef.current) {
            terminalHandledRef.current = true;
            logger.debug('Terminal state detected', {
                component: 'StreamingHandlers',
                sessionId
            });

            // Fetch results when workflow completes
            let results = null;
            try {
                logger.debug('Fetching results for completed workflow', {
                    component: 'StreamingHandlers',
                    sessionId
                });
                results = await workflowAPI.getWorkflowResults(sessionId);
            } catch (e) {
                logger.error('Failed to fetch results for completed workflow', e, {
                    component: 'StreamingHandlers',
                    sessionId
                });
            }

            // Notify terminal state with results
            if (callbacks.onTerminal) {
                await callbacks.onTerminal(status, results);
            }
        }
    };

    const handleError = (error: Error) => {
        logger.error('Streaming error', error, {
            component: 'StreamingHandlers',
            sessionId
        });
        if (callbacks.onError) {
            callbacks.onError(error);
        }
    };

    const handleComplete = async () => {
        logger.info('Stream completed, checking if terminal handled', {
            component: 'StreamingHandlers',
            sessionId,
            terminalHandled: terminalHandledRef.current
        });

        // If terminal state was already handled, skip fetching
        if (terminalHandledRef.current) {
            logger.debug('Terminal state already handled, skipping duplicate fetch', {
                component: 'StreamingHandlers',
                sessionId
            });
            return;
        }

        // When stream ends, fetch final status to ensure we have the complete state
        try {
            const finalStatus = await workflowAPI.getWorkflowStatus(sessionId);
            logger.info('Fetched final status after stream completion', {
                component: 'StreamingHandlers',
                sessionId,
                status: finalStatus.status
            });

            // Update with final status
            if (callbacks.onStatus) {
                await callbacks.onStatus(finalStatus);
            }

            // If it's a terminal state, fetch results
            const isTerminal = isTerminalStatus(finalStatus.status);
            if (isTerminal && !terminalHandledRef.current) {
                terminalHandledRef.current = true;
                let results = null;
                try {
                    results = await workflowAPI.getWorkflowResults(sessionId);
                } catch (e) {
                    logger.error('Failed to fetch results after stream completion', e, {
                        component: 'StreamingHandlers',
                        sessionId
                    });
                }

                if (callbacks.onTerminal) {
                    await callbacks.onTerminal(finalStatus, results);
                }
            }
        } catch (e) {
            logger.error('Failed to fetch final status after stream completion', e, {
                component: 'StreamingHandlers',
                sessionId
            });
        }
    };

    const handleReconnect = async () => {
        logger.info('Stream reconnected, fetching latest state', {
            component: 'StreamingHandlers',
            sessionId
        });

        // Fetch latest workflow status to ensure we didn't miss updates
        try {
            const latestStatus = await workflowAPI.getWorkflowStatus(sessionId);
            if (callbacks.onStatus) {
                await callbacks.onStatus(latestStatus);
            }
        } catch (e) {
            logger.error('Failed to fetch status after reconnection', e, {
                component: 'StreamingHandlers',
                sessionId
            });
        }
    };

    return {
        handleStatus,
        handleError,
        handleComplete,
        handleReconnect,
    };
}

