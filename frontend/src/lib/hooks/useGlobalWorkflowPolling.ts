'use client';

import { useEffect, useRef } from 'react';
import { workflowAPI } from '@/lib/api/workflow';
import { logger } from '@/lib/utils/logger';
import { workflowEvents } from './useActiveWorkflows';
import { useToast } from './useToast';

/**
 * Global polling hook that polls ALL active workflows regardless of current page
 * This ensures workflow updates are tracked even when not on the workflow page
 * 
 * @param activeSessionIds - List of active workflow session IDs to poll
 * @param excludeSessionId - Optional session ID to exclude from polling (e.g., when already being polled on /create/[id] or viewed on /playlist/[id])
 */
export function useGlobalWorkflowPolling(activeSessionIds: string[], excludeSessionId?: string | null) {
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const pollingStateRef = useRef<Map<string, { status: string; lastUpdate: number }>>(new Map());
    const { success, error: showErrorToast } = useToast();
    const excludeSessionIdRef = useRef(excludeSessionId);

    // Keep excluded session ref up to date
    useEffect(() => {
        excludeSessionIdRef.current = excludeSessionId;
    }, [excludeSessionId]);

    useEffect(() => {
        // Filter out the excluded session ID (if any)
        const sessionIdsToPoll = activeSessionIds.filter(id => id !== excludeSessionId);

        // If no active workflows to poll, clear interval and state
        if (sessionIdsToPoll.length === 0) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            pollingStateRef.current.clear();
            return;
        }

        const pollWorkflows = async () => {
            // Poll each active workflow (except the excluded one)
            const pollPromises = sessionIdsToPoll.map(async (sessionId) => {
                try {
                    const status = await workflowAPI.getWorkflowStatus(sessionId);
                    const prevState = pollingStateRef.current.get(sessionId);

                    // Check if status has changed
                    if (!prevState || prevState.status !== status.status) {
                        logger.debug('Global polling detected status change', {
                            component: 'useGlobalWorkflowPolling',
                            sessionId,
                            prevStatus: prevState?.status,
                            newStatus: status.status
                        });

                        // Update local state
                        pollingStateRef.current.set(sessionId, {
                            status: status.status,
                            lastUpdate: Date.now()
                        });

                        // Dispatch update event
                        workflowEvents.updated({
                            sessionId: status.session_id,
                            status: status.status,
                            moodPrompt: status.mood_prompt,
                            startedAt: status.created_at,
                        });

                        // If terminal state, show toast and remove from tracking
                        if (status.status === 'completed' || status.status === 'failed') {
                            logger.info('Workflow reached terminal state in global polling', {
                                component: 'useGlobalWorkflowPolling',
                                sessionId,
                                status: status.status,
                                isExcluded: sessionId === excludeSessionIdRef.current
                            });

                            // Only show toast if this session is not excluded (not being viewed on a specific page)
                            const isExcluded = sessionId === excludeSessionIdRef.current;
                            if (!isExcluded) {
                                // Show toast notification for background workflow completion
                                if (status.status === 'completed') {
                                    success('Playlist ready!', {
                                        description: `"${status.mood_prompt}" is ready to view`,
                                        duration: 5000
                                    });
                                } else if (status.status === 'failed') {
                                    showErrorToast('Playlist creation failed', {
                                        description: status.error || 'Something went wrong',
                                        duration: 5000
                                    });
                                }
                            } else {
                                logger.debug('Skipping toast for excluded session', {
                                    component: 'useGlobalWorkflowPolling',
                                    sessionId
                                });
                            }

                            pollingStateRef.current.delete(sessionId);
                        }
                    }
                } catch (error) {
                    logger.error('Failed to poll workflow in global polling', error, {
                        component: 'useGlobalWorkflowPolling',
                        sessionId
                    });

                    // If workflow not found (404), remove from tracking
                    if (error instanceof Error && error.message.includes('404')) {
                        logger.info('Workflow not found, removing from tracking', {
                            component: 'useGlobalWorkflowPolling',
                            sessionId
                        });
                        workflowEvents.removed(sessionId);
                        pollingStateRef.current.delete(sessionId);
                    }
                }
            });

            await Promise.allSettled(pollPromises);
        };

        // Initial poll
        pollWorkflows();

        // Set up polling interval (every 10 seconds for global polling - less aggressive than page-specific)
        intervalRef.current = setInterval(pollWorkflows, 10000);

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [activeSessionIds, excludeSessionId, showErrorToast, success]);

    return null;
}

