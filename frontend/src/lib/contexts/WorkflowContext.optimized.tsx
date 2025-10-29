'use client';

import { logger } from '@/lib/utils/logger';
import { usePathname } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { WorkflowResults, WorkflowStatus } from '../api/workflow';
import { useWorkflowApi, useWorkflowSSE } from '../hooks/workflow';
import { WorkflowContextType, WorkflowProviderProps, WorkflowState } from '../types/workflow';

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export function WorkflowProvider({ children }: WorkflowProviderProps) {
    const pathname = usePathname();
    const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const api = useWorkflowApi();

    const [workflowState, setWorkflowState] = useState<WorkflowState>({
        sessionId: null,
        status: null,
        currentStep: '',
        moodPrompt: '',
        moodAnalysis: undefined,
        recommendations: [],
        error: null,
        isLoading: false,
        awaitingInput: false,
    });

    // Only stream when on /create/[id] pages
    const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    const shouldStream = useMemo(() =>
        Boolean(workflowState.sessionId && isCreatePage),
        [workflowState.sessionId, isCreatePage]
    );

    // Create stable callback refs to avoid stale closures
    const handleStatusUpdate = useCallback(async (status: WorkflowStatus) => {
        // For non-terminal states, just update the status
        logger.debug('Status update', {
            to: status.status,
            currentStep: status.current_step,
        });
        setWorkflowState(prev => ({
            ...prev,
            status: status.status,
            currentStep: status.current_step,
            awaitingInput: status.awaiting_input,
            error: status.error || null,
            moodAnalysis: status.mood_analysis || prev.moodAnalysis,
            totalLLMCost: status.total_llm_cost_usd,
            metadata: status.metadata || prev.metadata,
        }));
    }, []);

    const handleTerminalUpdate = useCallback(async (status: WorkflowStatus, results: WorkflowResults | null) => {
        // Update state with terminal status and results
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
            totalLLMCost: status.total_llm_cost_usd,
            isLoading: false,
        }));
    }, []);

    const handleError = useCallback((error: Error) => {
        logger.error('Workflow streaming error', error, { component: 'WorkflowContext' });
        setWorkflowState(prev => ({
            ...prev,
            error: 'Connection error. Please check your internet connection.',
        }));
    }, []);

    const handleAwaitingInput = useCallback(() => {
        logger.debug('Workflow awaiting user input', { component: 'WorkflowContext' });
    }, []);

    // Use the SSE hook with callbacks (falls back to polling if SSE not supported)
    // Cast to satisfy type - 'started' is a valid transient status
    useWorkflowSSE(
        workflowState.sessionId,
        workflowState.status === 'started' ? 'pending' : workflowState.status,
        {
            enabled: shouldStream,
            callbacks: {
                onStatus: handleStatusUpdate,
                onTerminal: handleTerminalUpdate,
                onError: handleError,
                onAwaitingInput: handleAwaitingInput,
            },
        }
    );

    // Memoized workflow actions
    const startWorkflow = useCallback(async (moodPrompt: string, genreHint?: string) => {
        setWorkflowState(prev => ({
            ...prev,
            isLoading: true,
            error: null,
            moodPrompt,
        }));

        try {
            const response = await api.startWorkflow(moodPrompt, genreHint);

            setWorkflowState(prev => ({
                ...prev,
                sessionId: response.session_id,
                status: response.status,
                isLoading: true, // Keep loading true so redirect happens
            }));

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to start workflow';
            setWorkflowState(prev => ({
                ...prev,
                error: errorMessage,
                isLoading: false,
            }));
            throw error;
        }
    }, [api]);

    const loadWorkflow = useCallback(async (sessionId: string) => {
        logger.debug('[loadWorkflow] Called', {
            component: 'WorkflowContext',
            sessionId,
            state: {
                sessionId: workflowState.sessionId,
                status: workflowState.status,
                isLoading: workflowState.isLoading,
            }
        });

        // Prevent concurrent calls
        if (workflowState.isLoading) {
            logger.debug('[loadWorkflow] Already loading, skipping duplicate call', { component: 'WorkflowContext' });
            return;
        }

        // If we already have this session loaded and it's terminal, no need to reload
        if (workflowState.sessionId === sessionId &&
            (workflowState.status === 'completed' || workflowState.status === 'failed')) {
            logger.debug('[loadWorkflow] Workflow already loaded with terminal status, skipping', {
                component: 'WorkflowContext',
                sessionId,
                status: workflowState.status
            });
            return;
        }

        setWorkflowState(prev => ({
            ...prev,
            sessionId,
            isLoading: true,
            error: null,
        }));

        try {
            logger.debug('[loadWorkflow] Fetching workflow status', { component: 'WorkflowContext', sessionId });
            const status = await api.loadWorkflowStatus(sessionId);

            logger.debug('[loadWorkflow] Status received', {
                component: 'WorkflowContext',
                sessionId,
                status: status.status,
            });

            // If workflow is in terminal state, fetch full results
            const isTerminal = status.status === 'completed' || status.status === 'failed';
            let results: WorkflowResults | null = null;

            if (isTerminal) {
                logger.debug('[loadWorkflow] Terminal state detected, fetching results', { component: 'WorkflowContext', sessionId });
                try {
                    results = await api.loadWorkflowResults(sessionId);
                } catch (error) {
                    logger.error('[loadWorkflow] Failed to fetch results', error, { component: 'WorkflowContext', sessionId });
                }
            }

            setWorkflowState(prev => ({
                ...prev,
                sessionId: status.session_id,
                status: status.status,
                currentStep: status.current_step,
                moodPrompt: status.mood_prompt,
                moodAnalysis: results?.mood_analysis || status.mood_analysis,
                recommendations: results?.recommendations || [],
                playlist: results?.playlist,
                awaitingInput: status.awaiting_input,
                error: status.error || null,
                totalLLMCost: status.total_llm_cost_usd,
                metadata: status.metadata || prev.metadata,
                isLoading: false,
            }));

            logger.debug('[loadWorkflow] State updated', {
                component: 'WorkflowContext',
                sessionId,
                status: status.status,
                isLoading: !isTerminal
            });

        } catch (error) {
            logger.error('[loadWorkflow] Error', error, { component: 'WorkflowContext', sessionId });
            const errorMessage = error instanceof Error ? error.message : 'Failed to load workflow';
            setWorkflowState(prev => ({
                ...prev,
                error: errorMessage,
                isLoading: false,
            }));
        }
    }, [api, workflowState.sessionId, workflowState.status, workflowState.isLoading]);

    const stopWorkflow = useCallback(() => {
        logger.info('Stopping workflow', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
        setWorkflowState(prev => ({ ...prev, isLoading: false }));
    }, [workflowState.sessionId]);

    const resetWorkflow = useCallback(() => {
        logger.info('Resetting workflow', { component: 'WorkflowContext' });
        setWorkflowState({
            sessionId: null,
            status: null,
            currentStep: '',
            moodPrompt: '',
            moodAnalysis: undefined,
            recommendations: [],
            playlist: undefined,
            error: null,
            isLoading: false,
            awaitingInput: false,
        });
    }, []);

    const applyCompletedEdit = useCallback(async (
        editType: 'reorder' | 'remove' | 'add',
        options: { trackId?: string; newPosition?: number; trackUri?: string }
    ) => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }

        await api.applyEdit(workflowState.sessionId, editType, options);

        // Refresh results after a short delay to get updated recommendations
        if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
        }

        refreshTimeoutRef.current = setTimeout(async () => {
            try {
                const results = await api.loadWorkflowResults(workflowState.sessionId!);
                setWorkflowState(prev => ({
                    ...prev,
                    recommendations: results.recommendations || prev.recommendations,
                    metadata: results.metadata,
                }));
            } catch (error) {
                logger.error('Failed to refresh after edit', error, { component: 'WorkflowContext' });
            }
        }, 500);
    }, [workflowState.sessionId, api]);

    const searchTracks = useCallback(async (query: string, limit: number = 10) => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }
        return api.searchTracks(query, limit);
    }, [workflowState.sessionId, api]);

    const refreshResults = useCallback(async () => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }

        const results = await api.loadWorkflowResults(workflowState.sessionId);
        setWorkflowState(prev => ({
            ...prev,
            recommendations: results.recommendations || prev.recommendations,
            moodAnalysis: results.mood_analysis || prev.moodAnalysis,
            metadata: results.metadata,
        }));
    }, [workflowState.sessionId, api]);

    const saveToSpotify = useCallback(async () => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }
        return api.saveToSpotify(workflowState.sessionId);
    }, [workflowState.sessionId, api]);

    const syncFromSpotify = useCallback(async () => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }
        return api.syncFromSpotify(workflowState.sessionId);
    }, [workflowState.sessionId, api]);

    const clearError = useCallback(() => {
        setWorkflowState(prev => ({ ...prev, error: null }));
    }, []);

    // Listen for auth events to reset workflow state
    useEffect(() => {
        const handleAuthLogout = () => {
            logger.info('Auth logout detected, resetting workflow', { component: 'WorkflowContext' });
            resetWorkflow();
        };

        window.addEventListener('auth-logout', handleAuthLogout);
        return () => {
            window.removeEventListener('auth-logout', handleAuthLogout);
        };
    }, [resetWorkflow]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current);
            }
        };
    }, []);

    // Memoize the context value to prevent unnecessary re-renders
    const value = useMemo<WorkflowContextType>(() => ({
        workflowState,
        startWorkflow,
        loadWorkflow,
        stopWorkflow,
        resetWorkflow,
        applyCompletedEdit,
        searchTracks,
        refreshResults,
        saveToSpotify,
        syncFromSpotify,
        clearError,
    }), [
        workflowState,
        startWorkflow,
        loadWorkflow,
        stopWorkflow,
        resetWorkflow,
        applyCompletedEdit,
        searchTracks,
        refreshResults,
        saveToSpotify,
        syncFromSpotify,
        clearError,
    ]);

    return <WorkflowContext.Provider value={value}>{children}</WorkflowContext.Provider>;
}

export function useWorkflow() {
    const context = useContext(WorkflowContext);
    if (context === undefined) {
        throw new Error('useWorkflow must be used within a WorkflowProvider');
    }
    return context;
}

