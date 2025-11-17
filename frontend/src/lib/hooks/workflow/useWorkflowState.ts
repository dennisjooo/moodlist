'use client';
import type { WorkflowStatus, WorkflowResults } from '@/lib/api/workflow';
import type { AnchorTrack, WorkflowState } from '@/lib/types/workflow';
import { logger } from '@/lib/utils/logger';
import { shouldAcceptStatusUpdate } from '@/lib/utils/workflow';
import { useCallback, useRef, useState } from 'react';
import { useToast } from '../ui/useToast';
import { workflowEvents } from './useActiveWorkflows';

/**
 * Normalize anchor tracks from backend format to frontend format
 */
function normalizeAnchorTracks(tracks?: Array<{
    id: string;
    name: string;
    artists: Array<{ name: string }> | string[];
    album?: { name: string };
    user_mentioned?: boolean;
    user_mentioned_artist?: boolean;
    anchor_type?: 'user' | 'genre';
    protected?: boolean;
}>): AnchorTrack[] | undefined {
    if (!tracks || tracks.length === 0) return undefined;

    return tracks.map(track => ({
        id: track.id,
        name: track.name,
        artists: Array.isArray(track.artists)
            ? track.artists.map(a => typeof a === 'string' ? a : a.name)
            : [],
        album: typeof track.album === 'object' ? track.album?.name : track.album,
        user_mentioned: track.user_mentioned,
        user_mentioned_artist: track.user_mentioned_artist,
        anchor_type: track.anchor_type,
        protected: track.protected,
    }));
}

const initialWorkflowState: WorkflowState = {
    sessionId: null,
    status: null,
    currentStep: '',
    moodPrompt: '',
    moodAnalysis: undefined,
    recommendations: [],
    anchorTracks: undefined,
    error: null,
    isLoading: false,
    awaitingInput: false,
    totalLLMCost: 0,
    totalPromptTokens: 0,
    totalCompletionTokens: 0,
    totalTokens: 0,
};

export function useWorkflowState() {
    const [workflowState, setWorkflowState] = useState<WorkflowState>(initialWorkflowState);
    const { success, error: showErrorToast } = useToast();

    // Track if we've already shown terminal toast for this session
    const terminalToastShownRef = useRef<string | null>(null);

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
                anchorTracks: normalizeAnchorTracks(status.anchor_tracks) || prev.anchorTracks,
                metadata: status.metadata || prev.metadata,
                totalLLMCost: status.total_llm_cost_usd ?? prev.totalLLMCost,
                totalPromptTokens: status.total_prompt_tokens ?? prev.totalPromptTokens,
                totalCompletionTokens: status.total_completion_tokens ?? prev.totalCompletionTokens,
                totalTokens: status.total_tokens ?? prev.totalTokens,
            };
        });
    }, []);

    const handleTerminalUpdate = useCallback(async (status: WorkflowStatus, results: WorkflowResults | null) => {
        logger.debug('Terminal state reached', {
            to: status.status,
            sessionId: status.session_id,
        });

        // Create a unique key for this terminal state (session + status)
        const terminalKey = `${status.session_id}-${status.status}`;

        // Only show toast if we haven't shown it for this session's terminal state yet
        if (terminalToastShownRef.current !== terminalKey) {
            terminalToastShownRef.current = terminalKey;

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
        } else {
            logger.debug('Skipping duplicate terminal toast', {
                component: 'useWorkflowState',
                sessionId: status.session_id,
                status: status.status,
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
            anchorTracks: normalizeAnchorTracks(status.anchor_tracks) || prev.anchorTracks,
            playlist: results?.playlist || prev.playlist,
            totalLLMCost: status.total_llm_cost_usd ?? prev.totalLLMCost,
            totalPromptTokens: status.total_prompt_tokens ?? prev.totalPromptTokens,
            totalCompletionTokens: status.total_completion_tokens ?? prev.totalCompletionTokens,
            totalTokens: status.total_tokens ?? prev.totalTokens,
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
        terminalToastShownRef.current = null;
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
