'use client';

import { useEffect, useRef } from 'react';
import { sseManager } from '../sseManager';
import { pollingManager } from '../pollingManager';
import { workflowAPI } from '../api/workflow';
import type { WorkflowStatus, WorkflowResults } from '../api/workflow';
import { logger } from '@/lib/utils/logger';

interface SSECallbacks {
    onStatus?: (status: WorkflowStatus) => void | Promise<void>;
    onError?: (error: Error) => void;
    onAwaitingInput?: () => void;
    onTerminal?: (status: WorkflowStatus, results: WorkflowResults | null) => void | Promise<void>;
}

interface UseWorkflowSSEOptions {
    enabled?: boolean;
    callbacks?: SSECallbacks;
    useFallback?: boolean; // Whether to fallback to polling if SSE not supported
}

/**
 * Custom hook to manage workflow SSE connection lifecycle
 * Automatically starts/stops SSE streaming based on session ID and enabled flag
 * Falls back to polling if SSE is not supported
 */
export function useWorkflowSSE(
    sessionId: string | null,
    status: WorkflowStatus['status'] | null,
    options: UseWorkflowSSEOptions = {}
) {
    const { enabled = true, callbacks = {}, useFallback = true } = options;
    const callbacksRef = useRef(callbacks);
    const isUsingSSE = useRef(false);
    const currentStatusRef = useRef(status);

    // Keep callbacks ref up to date
    useEffect(() => {
        callbacksRef.current = callbacks;
    }, [callbacks]);

    // Keep current status ref up to date
    useEffect(() => {
        currentStatusRef.current = status;
    }, [status]);

    useEffect(() => {
        // Don't connect if no session or disabled
        if (!sessionId || !enabled) {
            logger.debug('SSE not starting', {
                component: 'useWorkflowSSE',
                sessionId,
                enabled,
                reason: !sessionId ? 'no sessionId' : 'disabled'
            });
            return;
        }

        // Check if workflow is in a terminal state at connection time
        const isTerminalState = currentStatusRef.current === 'completed' || currentStatusRef.current === 'failed';
        if (isTerminalState) {
            logger.debug('Workflow in terminal state, not starting SSE', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });
            return;
        }

        logger.info('SSE hook effect triggered', {
            component: 'useWorkflowSSE',
            sessionId,
            status: currentStatusRef.current,
            enabled
        });

        // Check SSE support
        const sseSupported = sseManager.isSupported();

        if (!sseSupported && !useFallback) {
            logger.warn('SSE not supported and fallback disabled', {
                component: 'useWorkflowSSE',
                sessionId
            });
            if (callbacksRef.current.onError) {
                callbacksRef.current.onError(new Error('SSE not supported by browser'));
            }
            return;
        }

        // Use SSE if supported, otherwise fallback to polling
        if (sseSupported) {
            logger.info('Starting SSE streaming', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });

            isUsingSSE.current = true;

            const handleStatus = async (status: WorkflowStatus) => {
                // Notify status change
                if (callbacksRef.current.onStatus) {
                    await callbacksRef.current.onStatus(status);
                }

                // Handle awaiting input state
                if (status.awaiting_input && callbacksRef.current.onAwaitingInput) {
                    callbacksRef.current.onAwaitingInput();
                }

                // If workflow reached terminal state, fetch results
                const isTerminal = status.status === 'completed' || status.status === 'failed';

                if (isTerminal) {
                    logger.debug('Terminal state detected via SSE', {
                        component: 'useWorkflowSSE',
                        sessionId
                    });

                    // Fetch results when workflow completes
                    let results = null;
                    try {
                        logger.debug('Fetching results for completed workflow', {
                            component: 'useWorkflowSSE',
                            sessionId
                        });
                        results = await workflowAPI.getWorkflowResults(sessionId);
                    } catch (e) {
                        logger.error('Failed to fetch results for completed workflow', e, {
                            component: 'useWorkflowSSE',
                            sessionId
                        });
                    }

                    // Notify terminal state with results
                    if (callbacksRef.current.onTerminal) {
                        await callbacksRef.current.onTerminal(status, results);
                    }

                    logger.info('Terminal state set with results, SSE will close', {
                        component: 'useWorkflowSSE',
                        sessionId
                    });
                }
            };

            const handleError = (error: Error) => {
                logger.error('SSE streaming error', error, {
                    component: 'useWorkflowSSE',
                    sessionId
                });
                if (callbacksRef.current.onError) {
                    callbacksRef.current.onError(error);
                }
            };

            const handleComplete = async () => {
                logger.info('SSE stream completed, fetching final status', {
                    component: 'useWorkflowSSE',
                    sessionId
                });

                // When stream ends, fetch final status to ensure we have the complete state
                try {
                    const finalStatus = await workflowAPI.getWorkflowStatus(sessionId);
                    logger.info('Fetched final status after SSE completion', {
                        component: 'useWorkflowSSE',
                        sessionId,
                        status: finalStatus.status
                    });

                    // Update with final status
                    if (callbacksRef.current.onStatus) {
                        await callbacksRef.current.onStatus(finalStatus);
                    }

                    // If it's a terminal state, fetch results
                    const isTerminal = finalStatus.status === 'completed' || finalStatus.status === 'failed';
                    if (isTerminal) {
                        let results = null;
                        try {
                            results = await workflowAPI.getWorkflowResults(sessionId);
                        } catch (e) {
                            logger.error('Failed to fetch results after SSE completion', e, {
                                component: 'useWorkflowSSE',
                                sessionId
                            });
                        }

                        if (callbacksRef.current.onTerminal) {
                            await callbacksRef.current.onTerminal(finalStatus, results);
                        }
                    }
                } catch (e) {
                    logger.error('Failed to fetch final status after SSE completion', e, {
                        component: 'useWorkflowSSE',
                        sessionId
                    });
                }
            };

            const handleReconnect = async () => {
                logger.info('SSE reconnected, fetching latest state', {
                    component: 'useWorkflowSSE',
                    sessionId
                });

                // Fetch latest workflow status to ensure we didn't miss updates
                try {
                    const latestStatus = await workflowAPI.getWorkflowStatus(sessionId);
                    if (callbacksRef.current.onStatus) {
                        await callbacksRef.current.onStatus(latestStatus);
                    }
                } catch (e) {
                    logger.error('Failed to fetch status after reconnection', e, {
                        component: 'useWorkflowSSE',
                        sessionId
                    });
                }
            };

            // Start SSE streaming
            sseManager.startStreaming(sessionId, {
                onStatus: handleStatus,
                onError: handleError,
                onComplete: handleComplete,
                onReconnect: handleReconnect,
            });

        } else if (useFallback) {
            // Fallback to polling
            logger.info('SSE not supported, falling back to polling', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });

            isUsingSSE.current = false;

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
                        component: 'useWorkflowSSE',
                        sessionId
                    });
                    pollingManager.stopPolling(sessionId);

                    // Fetch results when workflow completes
                    let results = null;
                    try {
                        logger.debug('Fetching results for completed workflow', {
                            component: 'useWorkflowSSE',
                            sessionId
                        });
                        results = await workflowAPI.getWorkflowResults(sessionId);
                    } catch (e) {
                        logger.error('Failed to fetch results for completed workflow', e, {
                            component: 'useWorkflowSSE',
                            sessionId
                        });
                    }

                    // Notify terminal state with results
                    if (callbacksRef.current.onTerminal) {
                        await callbacksRef.current.onTerminal(status, results);
                    }

                    logger.info('Terminal state set with results, polling stopped', {
                        component: 'useWorkflowSSE',
                        sessionId
                    });
                }
            };

            const handleError = (error: Error) => {
                logger.error('Workflow polling error', error, {
                    component: 'useWorkflowSSE',
                    sessionId
                });
                if (callbacksRef.current.onError) {
                    callbacksRef.current.onError(error);
                }
            };

            const handleAwaitingInput = () => {
                logger.debug('Workflow awaiting user input', {
                    component: 'useWorkflowSSE',
                    sessionId
                });
                if (callbacksRef.current.onAwaitingInput) {
                    callbacksRef.current.onAwaitingInput();
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
        }

        return () => {
            // Cleanup on unmount or when dependencies change
            if (isUsingSSE.current) {
                logger.debug('Cleanup: stopping SSE stream', {
                    component: 'useWorkflowSSE',
                    sessionId
                });
                sseManager.stopStreaming(sessionId);
            } else {
                logger.debug('Cleanup: stopping polling', {
                    component: 'useWorkflowSSE',
                    sessionId
                });
                pollingManager.stopPolling(sessionId);
            }
        };
    }, [sessionId, enabled, useFallback]);
}

