'use client';

import { useEffect, useState } from 'react';
import { logger } from '@/lib/utils/logger';
import { isTerminalStatus } from '@/lib/utils/workflow';

export interface ActiveWorkflow {
    sessionId: string;
    status: string;
    moodPrompt: string;
    startedAt: string;
}

const STORAGE_KEY = 'moodlist_active_workflows';
const MAX_WORKFLOWS = 5; // Keep track of up to 5 active workflows

/**
 * Hook to manage and track active workflows globally across the app
 */
export function useActiveWorkflows() {
    const [activeWorkflows, setActiveWorkflows] = useState<ActiveWorkflow[]>([]);

    // Load active workflows from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const workflows = JSON.parse(stored) as ActiveWorkflow[];
                setActiveWorkflows(workflows);
            }
        } catch (error) {
            logger.error('Failed to load active workflows from localStorage', error, {
                component: 'useActiveWorkflows'
            });
        }
    }, []);

    // Listen for workflow events
    useEffect(() => {
        const handleWorkflowStarted = (event: CustomEvent<ActiveWorkflow>) => {
            setActiveWorkflows(prev => {
                // Remove any existing workflow with same sessionId
                const filtered = prev.filter(w => w.sessionId !== event.detail.sessionId);
                // Add new workflow at the beginning
                const updated = [event.detail, ...filtered].slice(0, MAX_WORKFLOWS);

                // Persist to localStorage
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
                } catch (error) {
                    logger.error('Failed to save active workflows to localStorage', error, {
                        component: 'useActiveWorkflows'
                    });
                }

                return updated;
            });
        };

        const handleWorkflowUpdate = (event: CustomEvent<ActiveWorkflow>) => {
            setActiveWorkflows(prev => {
                const existing = prev.find(w => w.sessionId === event.detail.sessionId);

                // If workflow reached terminal status, remove it
                if (isTerminalStatus(event.detail.status)) {
                    const filtered = prev.filter(w => w.sessionId !== event.detail.sessionId);

                    // Persist to localStorage
                    try {
                        localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
                    } catch (error) {
                        logger.error('Failed to update active workflows in localStorage', error, {
                            component: 'useActiveWorkflows'
                        });
                    }

                    return filtered;
                }

                // Update existing workflow
                if (existing) {
                    const updated = prev.map(w =>
                        w.sessionId === event.detail.sessionId ? event.detail : w
                    );

                    // Persist to localStorage
                    try {
                        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
                    } catch (error) {
                        logger.error('Failed to update active workflows in localStorage', error, {
                            component: 'useActiveWorkflows'
                        });
                    }

                    return updated;
                }

                return prev;
            });
        };

        const handleWorkflowRemoved = (event: CustomEvent<{ sessionId: string }>) => {
            setActiveWorkflows(prev => {
                const filtered = prev.filter(w => w.sessionId !== event.detail.sessionId);

                // Persist to localStorage
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
                } catch (error) {
                    logger.error('Failed to remove workflow from localStorage', error, {
                        component: 'useActiveWorkflows'
                    });
                }

                return filtered;
            });
        };

        window.addEventListener('workflow-started', handleWorkflowStarted as EventListener);
        window.addEventListener('workflow-updated', handleWorkflowUpdate as EventListener);
        window.addEventListener('workflow-removed', handleWorkflowRemoved as EventListener);

        return () => {
            window.removeEventListener('workflow-started', handleWorkflowStarted as EventListener);
            window.removeEventListener('workflow-updated', handleWorkflowUpdate as EventListener);
            window.removeEventListener('workflow-removed', handleWorkflowRemoved as EventListener);
        };
    }, []);

    // Clean up old workflows on mount and periodically
    useEffect(() => {
        const cleanupOldWorkflows = () => {
            setActiveWorkflows(prev => {
                const now = Date.now();
                const ONE_HOUR = 60 * 60 * 1000;

                // Remove workflows older than 1 hour or in terminal state
                const filtered = prev.filter(w => {
                    const startedAt = new Date(w.startedAt).getTime();
                    const isOld = now - startedAt >= ONE_HOUR;
                    const isTerminal = isTerminalStatus(w.status);
                    return !isOld && !isTerminal;
                });

                if (filtered.length !== prev.length) {
                    try {
                        localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
                    } catch (error) {
                        logger.error('Failed to cleanup old workflows in localStorage', error, {
                            component: 'useActiveWorkflows'
                        });
                    }
                }

                return filtered;
            });
        };

        // Cleanup on mount
        cleanupOldWorkflows();

        // Cleanup every 5 minutes
        const interval = setInterval(cleanupOldWorkflows, 5 * 60 * 1000);

        return () => clearInterval(interval);
    }, []);

    // Clear all workflows on logout
    useEffect(() => {
        const handleLogout = () => {
            setActiveWorkflows([]);
            try {
                localStorage.removeItem(STORAGE_KEY);
            } catch (error) {
                logger.error('Failed to clear workflows on logout', error, {
                    component: 'useActiveWorkflows'
                });
            }
        };

        window.addEventListener('auth-logout', handleLogout);
        return () => window.removeEventListener('auth-logout', handleLogout);
    }, []);

    return {
        activeWorkflows,
        hasActiveWorkflows: activeWorkflows.length > 0,
    };
}

/**
 * Helper functions to dispatch workflow events
 */
export const workflowEvents = {
    started: (workflow: ActiveWorkflow) => {
        window.dispatchEvent(new CustomEvent('workflow-started', { detail: workflow }));
    },
    updated: (workflow: ActiveWorkflow) => {
        window.dispatchEvent(new CustomEvent('workflow-updated', { detail: workflow }));
    },
    removed: (sessionId: string) => {
        window.dispatchEvent(new CustomEvent('workflow-removed', { detail: { sessionId } }));
    }
};

