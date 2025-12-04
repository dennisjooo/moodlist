import { useCallback, useRef } from 'react';
import { logger } from '@/lib/utils/logger';
import { workflowEvents } from './useActiveWorkflows';
import { useWorkflowApi } from './useWorkflowApi';
import type { WorkflowState } from '@/lib/types/workflow';
import { isTerminalStatus } from '@/lib/utils/workflow';

interface UseWorkflowActionsProps {
    workflowState: WorkflowState;
    setLoading: (isLoading: boolean, error?: string | null) => void;
    setWorkflowData: (data: Partial<WorkflowState>) => void;
}

export function useWorkflowActions({
    workflowState,
    setLoading,
    setWorkflowData
}: UseWorkflowActionsProps) {
    const api = useWorkflowApi();
    const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const loadWorkflowCost = useCallback(async (sessionId: string) => {
        if (!sessionId) {
            return;
        }

        try {
            const costSummary = await api.loadWorkflowCost(sessionId);
            setWorkflowData({
                totalLLMCost: costSummary.total_llm_cost_usd,
                totalPromptTokens: costSummary.total_prompt_tokens,
                totalCompletionTokens: costSummary.total_completion_tokens,
                totalTokens: costSummary.total_tokens,
            });
        } catch (error) {
            logger.warn('Failed to load workflow cost summary', {
                component: 'useWorkflowActions',
                sessionId,
                error: error instanceof Error ? error.message : String(error),
            });
        }
    }, [api, setWorkflowData]);

    const startWorkflow = useCallback(async (moodPrompt: string, genreHint?: string) => {
        setWorkflowData({
            isLoading: true,
            error: null,
            moodPrompt,
            totalLLMCost: 0,
            totalPromptTokens: 0,
            totalCompletionTokens: 0,
            totalTokens: 0,
        });

        try {
            const response = await api.startWorkflow(moodPrompt, genreHint);

            setWorkflowData({
                sessionId: response.session_id,
                status: response.status,
                isLoading: true, // Keep loading true so redirect happens
                totalLLMCost: 0,
                totalPromptTokens: 0,
                totalCompletionTokens: 0,
                totalTokens: 0,
            });

            // Dispatch workflow started event asynchronously to avoid setState during render
            setTimeout(() => {
                workflowEvents.started({
                    sessionId: response.session_id,
                    status: response.status,
                    moodPrompt,
                    startedAt: new Date().toISOString(),
                });
            }, 0);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to start workflow';
            setWorkflowData({
                error: errorMessage,
                isLoading: false,
            });
            throw error;
        }
    }, [api, setWorkflowData]);

    const startRemix = useCallback(async (playlistId: string, source: string, moodPrompt?: string) => {
        setWorkflowData({
            isLoading: true,
            error: null,
            moodPrompt: moodPrompt || '',
            totalLLMCost: 0,
            totalPromptTokens: 0,
            totalCompletionTokens: 0,
            totalTokens: 0,
        });

        try {
            const response = await api.remixPlaylist({
                playlist_id: playlistId,
                source,
                mood_prompt: moodPrompt
            });

            setWorkflowData({
                sessionId: response.session_id,
                status: response.status,
                isLoading: true,
                totalLLMCost: 0,
                totalPromptTokens: 0,
                totalCompletionTokens: 0,
                totalTokens: 0,
            });

            setTimeout(() => {
                workflowEvents.started({
                    sessionId: response.session_id,
                    status: response.status,
                    moodPrompt: response.mood_prompt,
                    startedAt: new Date().toISOString(),
                });
            }, 0);
            
            return response;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to start remix';
            setWorkflowData({
                error: errorMessage,
                isLoading: false,
            });
            throw error;
        }
    }, [api, setWorkflowData]);

    const loadWorkflow = useCallback(async (sessionId: string) => {
        logger.debug('[loadWorkflow] Called', {
            component: 'useWorkflowActions',
            sessionId,
            state: {
                sessionId: workflowState.sessionId,
                status: workflowState.status,
                isLoading: workflowState.isLoading,
            }
        });

        // Prevent concurrent calls
        if (workflowState.isLoading) {
            logger.debug('[loadWorkflow] Already loading, skipping duplicate call', { component: 'useWorkflowActions' });
            return;
        }

        // If we already have this session loaded and it's terminal, no need to reload
        if (workflowState.sessionId === sessionId &&
            isTerminalStatus(workflowState.status) &&
            workflowState.recommendations.length > 0) {
            logger.debug('[loadWorkflow] Already loaded and terminal, skipping', { component: 'useWorkflowActions', sessionId });
            return;
        }

        logger.debug('[loadWorkflow] Proceeding with API calls', { component: 'useWorkflowActions', sessionId });
        setLoading(true, null);

        try {
            logger.debug('[loadWorkflow] Fetching status and cost in parallel', { component: 'useWorkflowActions', sessionId });
            // Load workflow status and cost in parallel for better performance
            const [status] = await Promise.all([
                api.loadWorkflowStatus(sessionId),
                loadWorkflowCost(sessionId),
            ]);

            // Only load results if workflow is in terminal state (completed or failed)
            let results = null;
            const isTerminal = isTerminalStatus(status.status);
            if (isTerminal) {
                logger.debug('Workflow is terminal, loading results', { component: 'useWorkflowActions', sessionId });
                try {
                    results = await api.loadWorkflowResults(sessionId);
                } catch {
                    // Results might not be ready yet, that's ok
                    logger.warn('Results not ready yet for terminal workflow', { component: 'useWorkflowActions', sessionId });
                }
            } else {
                logger.debug('Workflow is active', { component: 'useWorkflowActions', status: status.status, sessionId });
            }

            setWorkflowData({
                sessionId: status.session_id,
                status: status.status,
                currentStep: status.current_step,
                moodPrompt: status.mood_prompt,
                moodAnalysis: results?.mood_analysis || status.mood_analysis,
                recommendations: results?.recommendations || [],
                playlist: results?.playlist,
                awaitingInput: status.awaiting_input,
                error: status.error || null,
                totalLLMCost: status.total_llm_cost_usd ?? workflowState.totalLLMCost ?? 0,
                totalPromptTokens: status.total_prompt_tokens ?? workflowState.totalPromptTokens ?? 0,
                totalCompletionTokens: status.total_completion_tokens ?? workflowState.totalCompletionTokens ?? 0,
                totalTokens: status.total_tokens ?? workflowState.totalTokens ?? 0,
                metadata: status.metadata || workflowState.metadata,
                isLoading: false,
            });

            logger.info('Workflow loaded', { component: 'useWorkflowActions', sessionId, status: status.status });

            // If workflow is active (not terminal), register it for global tracking asynchronously
            if (!isTerminal) {
                setTimeout(() => {
                    workflowEvents.started({
                        sessionId: status.session_id,
                        status: status.status,
                        moodPrompt: status.mood_prompt,
                        startedAt: status.created_at,
                    });
                }, 0);
            }

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load workflow';
            setWorkflowData({
                error: errorMessage,
                isLoading: false,
            });
            logger.error('Failed to load workflow for session', error, { component: 'useWorkflowActions', sessionId });
        }
    }, [api, workflowState, setLoading, setWorkflowData, loadWorkflowCost]);

    const stopWorkflow = useCallback(() => {
        // Dispatch workflow-removed event to clean up active workflows tracking
        if (workflowState.sessionId) {
            setTimeout(() => {
                workflowEvents.removed(workflowState.sessionId!);
            }, 0);
        }

        // SSE/Polling is handled by the hook, just reset state
        setWorkflowData({
            sessionId: null,
            status: null,
            currentStep: '',
            moodPrompt: '',
            moodAnalysis: undefined,
            recommendations: [],
            error: null,
            isLoading: false,
            awaitingInput: false,
            totalLLMCost: 0,
            totalPromptTokens: 0,
            totalCompletionTokens: 0,
            totalTokens: 0,
        });
    }, [workflowState.sessionId, setWorkflowData]);

    const refreshResults = useCallback(async () => {
        if (!workflowState.sessionId) return;

        // Don't fetch results if we're already in a terminal state and have results
        if (isTerminalStatus(workflowState.status) &&
            workflowState.recommendations.length > 0) {
            logger.debug('Results already loaded for terminal workflow, skipping refresh', { component: 'useWorkflowActions', sessionId: workflowState.sessionId });
            return;
        }

        logger.debug('Fetching results', { component: 'useWorkflowActions', sessionId: workflowState.sessionId });
        setLoading(true, null);

        try {
            const results = await api.loadWorkflowResults(workflowState.sessionId);
            setWorkflowData({
                recommendations: results.recommendations,
                playlist: results.playlist,
                isLoading: false,
            });
            await loadWorkflowCost(workflowState.sessionId);
            logger.info('Results fetched successfully', { component: 'useWorkflowActions', sessionId: workflowState.sessionId });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to refresh results';
            setWorkflowData({
                error: errorMessage,
                isLoading: false,
            });
            logger.error('Failed to fetch results', error, { component: 'useWorkflowActions', sessionId: workflowState.sessionId });
        }
    }, [api, workflowState, setLoading, setWorkflowData, loadWorkflowCost]);

    const saveToSpotify = useCallback(async () => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }

        setLoading(true, null);

        try {
            const result = await api.saveToSpotify(workflowState.sessionId);

            // Update state with playlist information
            setWorkflowData({
                playlist: {
                    id: result.playlist_id,
                    name: result.playlist_name,
                    spotify_url: result.spotify_url,
                    spotify_uri: result.spotify_uri,
                },
                isLoading: false,
            });

            return result;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to save playlist to Spotify';
            setWorkflowData({
                error: errorMessage,
                isLoading: false,
            });
            throw error;
        }
    }, [api, workflowState.sessionId, setLoading, setWorkflowData]);

    const syncFromSpotify = useCallback(async () => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }

        // Don't show loading state for sync - it should be subtle
        try {
            const result = await api.syncFromSpotify(workflowState.sessionId);

            // Only update if sync was successful
            if (result.synced && result.recommendations) {
                setWorkflowData({
                    recommendations: result.recommendations || workflowState.recommendations,
                    playlist: result.playlist_data ? {
                        ...workflowState.playlist,
                        ...result.playlist_data,
                    } : workflowState.playlist,
                });
            }

            return result;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to sync from Spotify';
            logger.error('Sync error', error, { component: 'useWorkflowActions', errorMessage });
            // Don't set error in state for sync failures - they should be silent or handled by caller
            throw error;
        }
    }, [api, workflowState, setWorkflowData]);

    const applyCompletedEdit = useCallback(async (
        editType: 'reorder' | 'remove' | 'add',
        options: {
            trackId?: string;
            newPosition?: number;
            trackUri?: string;
        }
    ) => {
        if (!workflowState.sessionId) {
            throw new Error('No active workflow session');
        }

        // Don't set loading state - let the component handle optimistic updates
        try {
            await api.applyEdit(workflowState.sessionId, editType, options);

            // Use a debounced refresh to prevent race conditions from concurrent edits
            // This ensures only the latest edit triggers a state refresh
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current);
            }

            refreshTimeoutRef.current = setTimeout(async () => {
                try {
                    if (!workflowState.sessionId) return;
                    const results = await api.loadWorkflowResults(workflowState.sessionId);
                    setWorkflowData({
                        recommendations: results.recommendations,
                        playlist: results.playlist,
                    });
                } catch (error) {
                    logger.error('Failed to refresh workflow results after edit', error, { component: 'useWorkflowActions' });
                }
            }, 100); // 100ms debounce to batch concurrent edits
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to apply edit';
            setWorkflowData({
                error: errorMessage,
            });
            throw error;
        }
    }, [api, workflowState.sessionId, setWorkflowData]);

    const searchTracks = useCallback(async (query: string, limit: number = 20) => {
        return await api.searchTracks(query, limit);
    }, [api]);

    return {
        startWorkflow,
        startRemix,
        loadWorkflow,
        loadWorkflowCost,
        stopWorkflow,
        refreshResults,
        saveToSpotify,
        syncFromSpotify,
        applyCompletedEdit,
        searchTracks,
    };
}
