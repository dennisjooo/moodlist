import { useCallback, useState } from 'react';
import { logger } from '../utils/logger';
import { shouldAcceptStatusUpdate } from '../utils/workflow';
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

    const handleStatusUpdate = useCallback(async (status: WorkflowStatus) => {
        logger.debug('Status update', {
            to: status.status,
            currentStep: status.current_step,
            hasMoodAnalysis: !!status.mood_analysis
        });

        setWorkflowState(prev => {
            logger.debug('Previous state', {
                from: prev.status,
                to: status.status,
            });

            // Use utility function to determine if we should accept this update
            const shouldUpdate = shouldAcceptStatusUpdate(prev.status, status.status, !!status.error);

            if (!shouldUpdate) {
                logger.debug('Ignoring backwards status update', {
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
    }, []);

    const handleError = useCallback((error: Error) => {
        logger.error('Workflow streaming error', error, { component: 'useWorkflowState', sessionId: workflowState.sessionId });
        setWorkflowState(prev => ({
            ...prev,
            error: 'Connection error. Please check your internet connection.',
        }));
    }, [workflowState.sessionId]);

    const handleAwaitingInput = useCallback(() => {
        logger.debug('Workflow awaiting user input', { component: 'useWorkflowState', sessionId: workflowState.sessionId });
    }, [workflowState.sessionId]);

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
