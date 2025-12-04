'use client';

import { useMemo } from 'react';
import { workflowAPI } from '@/lib/api/workflow';
import type { StartRecommendationRequest, WorkflowStatus, WorkflowResults, WorkflowCostSummary } from '@/lib/api/workflow';
import { logger } from '@/lib/utils/logger';

/**
 * Custom hook that provides workflow API methods with consistent error handling
 * This hook doesn't manage state - it just provides API call wrappers
 */
export function useWorkflowApi() {
    const startWorkflow = async (moodPrompt: string, genreHint?: string) => {
        const request: StartRecommendationRequest = {
            mood_prompt: `${moodPrompt} ${genreHint ? `in the genre of ${genreHint}` : ''}`.trim(),
        };

        logger.info('Starting workflow', {
            component: 'useWorkflowApi',
            mood_prompt: request.mood_prompt
        });

        return await workflowAPI.startWorkflow(request);
    };

    const loadWorkflowStatus = async (sessionId: string): Promise<WorkflowStatus> => {
        logger.debug('Fetching workflow status', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.getWorkflowStatus(sessionId);
    };

    const loadWorkflowResults = async (sessionId: string): Promise<WorkflowResults> => {
        logger.debug('Fetching workflow results', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.getWorkflowResults(sessionId);
    };

    const loadWorkflowCost = async (sessionId: string): Promise<WorkflowCostSummary> => {
        logger.debug('Fetching workflow cost summary', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.getWorkflowCost(sessionId);
    };

    const saveToSpotify = async (sessionId: string) => {
        logger.info('Saving playlist to Spotify', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.saveToSpotify(sessionId);
    };

    const syncFromSpotify = async (sessionId: string) => {
        logger.info('Syncing from Spotify', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.syncFromSpotify(sessionId);
    };

    const applyEdit = async (
        sessionId: string,
        editType: 'reorder' | 'remove' | 'add',
        options: {
            trackId?: string;
            newPosition?: number;
            trackUri?: string;
        }
    ) => {
        logger.debug('Applying playlist edit', {
            component: 'useWorkflowApi',
            sessionId,
            editType,
            options
        });
        return await workflowAPI.applyCompletedPlaylistEdit(sessionId, editType, options);
    };

    const searchTracks = async (query: string, limit?: number) => {
        logger.debug('Searching tracks', {
            component: 'useWorkflowApi',
            query,
            limit
        });
        return await workflowAPI.searchTracks(query, limit);
    };

    const cancelWorkflow = async (sessionId: string) => {
        logger.info('Cancelling workflow', {
            component: 'useWorkflowApi',
            sessionId
        });
        return await workflowAPI.cancelWorkflow(sessionId);
    };

    const remixPlaylist = async (request: {
        playlist_id: string;
        source: string;
        mood_prompt?: string;
    }) => {
        logger.info('Starting remix workflow', {
            component: 'useWorkflowApi',
            ...request
        });
        return await workflowAPI.remixPlaylist(request);
    };

    return useMemo(() => ({
        startWorkflow,
        remixPlaylist,
        loadWorkflowStatus,
        loadWorkflowResults,
        loadWorkflowCost,
        saveToSpotify,
        syncFromSpotify,
        applyEdit,
        searchTracks,
        cancelWorkflow,
    }), []);
}
