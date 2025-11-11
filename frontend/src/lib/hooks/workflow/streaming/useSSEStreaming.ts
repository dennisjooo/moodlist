/**
 * SSE streaming handler for workflow status updates.
 */

import { sseManager } from '@/lib/sseManager';
import { logger } from '@/lib/utils/logger';
import type { StreamingCallbacks, StreamingHandler } from './streamingCallbacks';

export function useSSEStreaming(
    sessionId: string,
    callbacks: StreamingCallbacks,
    terminalHandledRef: React.RefObject<boolean>
): () => void {
    logger.info('Starting SSE streaming', {
        component: 'useSSEStreaming',
        sessionId
    });

    const handlers: StreamingHandler = {
        handleStatus: async (status) => {
            // Notify status change
            if (callbacks.onStatus) {
                await callbacks.onStatus(status);
            }

            // Handle awaiting input state
            if (status.awaiting_input && callbacks.onAwaitingInput) {
                callbacks.onAwaitingInput();
            }

            // If workflow reached terminal state, fetch results
            const isTerminal = status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled';

            if (isTerminal && !terminalHandledRef.current) {
                terminalHandledRef.current = true;
                logger.debug('Terminal state detected via SSE', {
                    component: 'useSSEStreaming',
                    sessionId
                });

                // Fetch results when workflow completes
                let results = null;
                try {
                    logger.debug('Fetching results for completed workflow', {
                        component: 'useSSEStreaming',
                        sessionId
                    });
                    const { workflowAPI } = await import('@/lib/api/workflow');
                    results = await workflowAPI.getWorkflowResults(sessionId);
                } catch (e) {
                    logger.error('Failed to fetch results for completed workflow', e, {
                        component: 'useSSEStreaming',
                        sessionId
                    });
                }

                // Notify terminal state with results
                if (callbacks.onTerminal) {
                    await callbacks.onTerminal(status, results);
                }

                logger.info('Terminal state set with results, SSE will close', {
                    component: 'useSSEStreaming',
                    sessionId
                });
            }
        },
        handleError: (error) => {
            logger.error('SSE streaming error', error, {
                component: 'useSSEStreaming',
                sessionId
            });
            if (callbacks.onError) {
                callbacks.onError(error);
            }
        },
        handleComplete: async () => {
            logger.info('SSE stream completed, checking if terminal handled', {
                component: 'useSSEStreaming',
                sessionId,
                terminalHandled: terminalHandledRef.current
            });

            // If terminal state was already handled, skip fetching
            if (terminalHandledRef.current) {
                logger.debug('Terminal state already handled, skipping duplicate fetch', {
                    component: 'useSSEStreaming',
                    sessionId
                });
                return;
            }

            // When stream ends, fetch final status to ensure we have the complete state
            try {
                const { workflowAPI } = await import('@/lib/api/workflow');
                const finalStatus = await workflowAPI.getWorkflowStatus(sessionId);
                logger.info('Fetched final status after SSE completion', {
                    component: 'useSSEStreaming',
                    sessionId,
                    status: finalStatus.status
                });

                // Update with final status
                if (callbacks.onStatus) {
                    await callbacks.onStatus(finalStatus);
                }

                // If it's a terminal state, fetch results
                const isTerminal = finalStatus.status === 'completed' || finalStatus.status === 'failed' || finalStatus.status === 'cancelled';
                if (isTerminal && !terminalHandledRef.current) {
                    terminalHandledRef.current = true;
                    let results = null;
                    try {
                        results = await workflowAPI.getWorkflowResults(sessionId);
                    } catch (e) {
                        logger.error('Failed to fetch results after SSE completion', e, {
                            component: 'useSSEStreaming',
                            sessionId
                        });
                    }

                    if (callbacks.onTerminal) {
                        await callbacks.onTerminal(finalStatus, results);
                    }
                }
            } catch (e) {
                logger.error('Failed to fetch final status after SSE completion', e, {
                    component: 'useSSEStreaming',
                    sessionId
                });
            }
        },
        handleReconnect: async () => {
            logger.info('SSE reconnected, fetching latest state', {
                component: 'useSSEStreaming',
                sessionId
            });

            // Fetch latest workflow status to ensure we didn't miss updates
            try {
                const { workflowAPI } = await import('@/lib/api/workflow');
                const latestStatus = await workflowAPI.getWorkflowStatus(sessionId);
                if (callbacks.onStatus) {
                    await callbacks.onStatus(latestStatus);
                }
            } catch (e) {
                logger.error('Failed to fetch status after reconnection', e, {
                    component: 'useSSEStreaming',
                    sessionId
                });
            }
        },
    };

    // Start SSE streaming
    sseManager.startStreaming(sessionId, {
        onStatus: handlers.handleStatus,
        onError: handlers.handleError,
        onComplete: handlers.handleComplete,
        onReconnect: handlers.handleReconnect,
    });

    // Return cleanup function
    return () => {
        logger.debug('Cleanup: stopping SSE stream', {
            component: 'useSSEStreaming',
            sessionId
        });
        sseManager.stopStreaming(sessionId);
    };
}

