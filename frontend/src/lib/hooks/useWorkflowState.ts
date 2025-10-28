import { useCallback, useState } from 'react';
import { logger } from '../utils/logger';
import { shouldAcceptStatusUpdate } from '../utils/workflow';
import { workflowEvents } from './useActiveWorkflows';
import { useToast } from './useToast';
import type { WorkflowResults, WorkflowStatus } from '../api/workflow';
import type { WorkflowState } from '../types/workflow';

const initialWorkflowState: WorkflowState = {
    sessionId: null,
    status: null,
    currentStep: '',
    moodPrompt: '',
    moodAnalysis: undefined,
    recommendations: [],
    error: null,
    isLoading: false,
    awaitingInput: false,
};

export function useWorkflowState() {
    const [workflowState, setWorkflowState] = useState<WorkflowState>(initialWorkflowState);
    const { success, error: showErrorToast } = useToast();

    const handleStatusUpdate = useCallback(async (status: WorkflowStatus) => {
        logger.info('Status update received', {
            component: 'useWorkflowState',
            newStatus: status.status,
            currentStep: status.current_step,
            hasMoodAnalysis: !!status.mood_analysis
        });

        setWorkflowState(prev => {
            logger.debug('Evaluating status update', {
                component: 'useWorkflowState',
                from: prev.status,
                to: status.status,
            });

            // Use utility function to determine if we should accept this update
            const shouldUpdate = shouldAcceptStatusUpdate(prev.status, status.status, !!status.error);

            if (!shouldUpdate) {
                logger.warn('Rejecting backwards status update', {
                    component: 'useWorkflowState',
                    from: prev.status,
                    to: status.status
                });
                // Keep previous state but update metadata if available
                return {
                    ...prev,
                    metadata: status.metadata || prev.metadata,
                    moodAnalysis: status.mood_analysis || prev.moodAnalysis,
                };
            }

            logger.info('Applying status update', {
                component: 'useWorkflowState',
                from: prev.status,
                to: status.status,
                currentStep: status.current_step
            });

            // Dispatch workflow update event asynchronously to avoid setState during render
            setTimeout(() => {
                workflowEvents.updated({
                    sessionId: status.session_id,
                    status: status.status,
                    moodPrompt: status.mood_prompt,
                    startedAt: status.created_at,
                });
            }, 0);

            return {
                ...prev,
                status: status.status,
                currentStep: status.current_step,
                awaitingInput: status.awaiting_input,
                error: status.error || null,
                moodAnalysis: status.mood_analysis || prev.moodAnalysis,
                metadata: status.metadata || prev.metadata,
            };
        });
    }, []);

    const handleTerminalUpdate = useCallback(async (status: WorkflowStatus, results: WorkflowResults | null) => {
        logger.debug('Terminal state reached', {
            to: status.status,
        });

        // Show toast notification based on final status
        if (status.status === 'completed') {
            const trackCount = results?.recommendations?.length || 0;
            success('Playlist created!', {
                description: trackCount > 0
                    ? `${trackCount} tracks ready for you`
                    : 'Your playlist is ready',
                duration: 5000
            });
        } else if (status.status === 'failed') {
            showErrorToast('Workflow failed', {
                description: status.error || 'Something went wrong creating your playlist',
                duration: 5000
            });
        }

        setWorkflowState(prev => ({
            ...prev,
            status: status.status,
            currentStep: status.current_step,
            awaitingInput: status.awaiting_input,
            error: status.error || null,
            moodAnalysis: results?.mood_analysis || prev.moodAnalysis,
            recommendations: results?.recommendations || prev.recommendations,
            playlist: results?.playlist || prev.playlist,
        }));
    }, [success, showErrorToast]);

    const handleError = useCallback((error: Error) => {
        logger.error('Workflow streaming error', error, { component: 'useWorkflowState' });
        setWorkflowState(prev => ({
            ...prev,
            error: 'Connection error. Please check your internet connection.',
        }));
    }, []);

    const handleAwaitingInput = useCallback(() => {
        logger.debug('Workflow awaiting user input', { component: 'useWorkflowState' });
    }, []);

    const setLoading = useCallback((isLoading: boolean, error: string | null = null) => {
        setWorkflowState(prev => ({ ...prev, isLoading, error: error || prev.error }));
    }, []);

    const setWorkflowData = useCallback((data: Partial<WorkflowState>) => {
        setWorkflowState(prev => ({ ...prev, ...data }));
    }, []);

    const resetWorkflow = useCallback(() => {
        logger.debug('Resetting workflow state, preserving auth', { component: 'useWorkflowState' });
        setWorkflowState(initialWorkflowState);
    }, []);

    const clearError = useCallback(() => {
        setWorkflowState(prev => ({ ...prev, error: null }));
    }, []);

    return {
        workflowState,
        handleStatusUpdate,
        handleTerminalUpdate,
        handleError,
        handleAwaitingInput,
        setLoading,
        setWorkflowData,
        resetWorkflow,
        clearError,
    };
}
