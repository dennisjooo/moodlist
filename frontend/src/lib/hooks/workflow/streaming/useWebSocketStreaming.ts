/**
 * WebSocket streaming handler for workflow status updates.
 */

import { wsManager } from '@/lib/wsManager';
import { logger } from '@/lib/utils/logger';
import type { StreamingCallbacks, StreamingHandler } from './streamingCallbacks';

export function useWebSocketStreaming(
    sessionId: string,
    callbacks: StreamingCallbacks,
    terminalHandledRef: React.RefObject<boolean>
): () => void {
    logger.info('Starting WebSocket streaming', {
        component: 'useWebSocketStreaming',
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
                logger.debug('Terminal state detected via WebSocket', {
                    component: 'useWebSocketStreaming',
                    sessionId
                });

                // Fetch results when workflow completes
                let results = null;
                try {
                    logger.debug('Fetching results for completed workflow', {
                        component: 'useWebSocketStreaming',
                        sessionId
                    });
                    const { workflowAPI } = await import('@/lib/api/workflow');
                    results = await workflowAPI.getWorkflowResults(sessionId);
                } catch (e) {
                    logger.error('Failed to fetch results for completed workflow', e, {
                        component: 'useWebSocketStreaming',
                        sessionId
                    });
                }

                // Notify terminal state with results
                if (callbacks.onTerminal) {
                    await callbacks.onTerminal(status, results);
                }

                logger.info('Terminal state set with results, WebSocket will close', {
                    component: 'useWebSocketStreaming',
                    sessionId
                });
            }
        },
        handleError: (error) => {
            logger.error('WebSocket streaming error', error, {
                component: 'useWebSocketStreaming',
                sessionId
            });
            if (callbacks.onError) {
                callbacks.onError(error);
            }
        },
        handleComplete: async () => {
            logger.info('WebSocket stream completed, checking if terminal handled', {
                component: 'useWebSocketStreaming',
                sessionId,
                terminalHandled: terminalHandledRef.current
            });

            // If terminal state was already handled, skip fetching
            if (terminalHandledRef.current) {
                logger.debug('Terminal state already handled, skipping duplicate fetch', {
                    component: 'useWebSocketStreaming',
                    sessionId
                });
                return;
            }

            // When stream ends, fetch final status to ensure we have the complete state
            try {
                const { workflowAPI } = await import('@/lib/api/workflow');
                const finalStatus = await workflowAPI.getWorkflowStatus(sessionId);
                logger.info('Fetched final status after WebSocket completion', {
                    component: 'useWebSocketStreaming',
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
                        logger.error('Failed to fetch results after WebSocket completion', e, {
                            component: 'useWebSocketStreaming',
                            sessionId
                        });
                    }

                    if (callbacks.onTerminal) {
                        await callbacks.onTerminal(finalStatus, results);
                    }
                }
            } catch (e) {
                logger.error('Failed to fetch final status after WebSocket completion', e, {
                    component: 'useWebSocketStreaming',
                    sessionId
                });
            }
        },
        handleReconnect: async () => {
            logger.info('WebSocket reconnected, fetching latest state', {
                component: 'useWebSocketStreaming',
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
                    component: 'useWebSocketStreaming',
                    sessionId
                });
            }
        },
    };

    // Start WebSocket streaming
    wsManager.startStreaming(sessionId, {
        onStatus: handlers.handleStatus,
        onError: handlers.handleError,
        onComplete: handlers.handleComplete,
        onReconnect: handlers.handleReconnect,
    });

    // Return cleanup function
    return () => {
        logger.debug('Cleanup: stopping WebSocket stream', {
            component: 'useWebSocketStreaming',
            sessionId
        });
        wsManager.stopStreaming(sessionId);
    };
}

