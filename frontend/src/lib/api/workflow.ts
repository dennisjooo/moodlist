// API service layer for agentic workflow endpoints
// Following the interfaces from FRONTEND_INTEGRATION_GUIDE.md

import { AxiosError, AxiosRequestConfig, isAxiosError } from 'axios';

import apiClient from '@/lib/axios';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import { extractAxiosErrorMessage, APIError } from '@/lib/utils/apiErrorHandling';

export interface StartRecommendationRequest {
    mood_prompt: string;
}

export interface StartRecommendationResponse {
    session_id: string;
    status: "started";
    mood_prompt: string;
    message: string;
}

export interface WorkflowStatus {
    session_id: string;
    status: "pending" | "analyzing_mood" | "gathering_seeds" |
    "generating_recommendations" | "evaluating_quality" |
    "optimizing_recommendations" | "ordering_playlist" | "awaiting_user_input" |
    "processing_edits" | "creating_playlist" |
    "completed" | "failed" | "cancelled";
    current_step: string;
    mood_prompt: string;
    mood_analysis?: {
        mood_interpretation: string;
        primary_emotion: string;
        energy_level: string;
        target_features: Record<string, number>;
        search_keywords: string[];
        color_scheme?: {
            primary: string;
            secondary: string;
            tertiary: string;
        };
    };
    anchor_tracks?: Array<{
        id?: string;
        track_id?: string;
        name?: string;
        track_name?: string;
        track?: Record<string, any>;
        artists?: Array<{ name: string }> | string[];
        album?: { name?: string; images?: Array<{ url: string }> } | string;
        user_mentioned?: boolean;
        user_mentioned_artist?: boolean;
        anchor_type?: 'user' | 'genre';
        protected?: boolean;
    }>;
    recommendations?: Array<{
        track_id: string;
        track_name: string;
        artists: string[];
        spotify_uri?: string;
        confidence_score: number;
        reasoning: string;
        source: string;
        user_mentioned?: boolean;
        user_mentioned_artist?: boolean;
        anchor_type?: string | null;
        protected?: boolean;
    }>;
    recommendation_count: number;
    seed_track_count?: number;
    user_top_tracks_count?: number;
    user_top_artists_count?: number;
    has_playlist: boolean;
    awaiting_input: boolean;
    error?: string;
    created_at: string;
    updated_at: string;
    total_llm_cost_usd?: number;
    total_prompt_tokens?: number;
    total_completion_tokens?: number;
    total_tokens?: number;
    metadata?: {
        iteration?: number;
        cohesion_score?: number;
    };
}

export interface WorkflowResults {
    session_id: string;
    status: string;
    mood_prompt: string;
    mood_analysis: {
        mood_interpretation: string;
        primary_emotion: string;
        energy_level: string;
        target_features: Record<string, number>;
        search_keywords: string[];
        color_scheme?: {
            primary: string;
            secondary: string;
            tertiary: string;
        };
    };
    recommendations: Array<{
        track_id: string;
        track_name: string;
        artists: string[];
        spotify_uri?: string;
        confidence_score: number;
        reasoning: string;
        source: string;
    }>;
    playlist?: {
        id: string;
        name: string;
        spotify_url?: string;
        spotify_uri?: string;
    };
    metadata: Record<string, unknown>;
}

export interface PlaylistEditRequest {
    edit_type: "reorder" | "remove" | "add" | "replace";
    track_id?: string;
    new_position?: number;
    reasoning?: string;
}

export interface PlaylistDetails {
    session_id: string;
    playlist: {
        playlist_id: string;
        playlist_name: string;
        spotify_url?: string;
        spotify_uri?: string;
    };
    tracks: Array<{
        position: number;
        track_id: string;
        track_name: string;
        artists: string[];
        spotify_uri?: string;
        confidence_score: number;
        reasoning: string;
        source: string;
    }>;
    mood_analysis: {
        mood_interpretation?: string;
        primary_emotion?: string;
        energy_level?: string;
        search_keywords?: string[];
        [key: string]: unknown;
    } | null;
    total_tracks: number;
    created_at: string;
}

export interface WorkflowCostSummary {
    session_id: string;
    invocation_count: number;
    total_llm_cost_usd: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
}

class WorkflowAPI {
    private async request<T>(
        endpoint: string,
        options: AxiosRequestConfig = {}
    ): Promise<T> {
        const url = `${config.api.baseUrl}${endpoint}`;
        logger.debug('API request', { component: 'WorkflowAPI', url, endpoint, method: options.method ?? 'get' });

        try {
            const response = await apiClient.request<T>({
                url: endpoint,
                ...options,
            });
            logger.info('API response', { component: 'WorkflowAPI', status: response.status, endpoint });

            return response.data;
        } catch (error) {
            logger.error('API request error', error, { component: 'WorkflowAPI', endpoint });

            if (isAxiosError(error)) {
                const axiosError = error as AxiosError;
                const status = axiosError.response?.status ?? 0;
                const errorMessage = extractAxiosErrorMessage(axiosError);

                throw new APIError(status, errorMessage, endpoint);
            }

            if (error instanceof APIError) {
                throw error;
            }

            throw new APIError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`, endpoint);
        }
    }

    async startWorkflow(request: StartRecommendationRequest): Promise<StartRecommendationResponse> {
        logger.info('Starting workflow', { component: 'WorkflowAPI', mood_prompt: request.mood_prompt });
        // Use query parameters as the backend expects
        const params = new URLSearchParams({
            mood_prompt: request.mood_prompt,
        });

        return this.request<StartRecommendationResponse>(
            `/api/agents/recommendations/start?${params.toString()}`,
            {
                method: 'POST',
            }
        );
    }

    async remixPlaylist(request: {
        playlist_id: string;
        source: string;
        mood_prompt?: string;
    }): Promise<StartRecommendationResponse> {
        logger.info('Starting remix workflow', { component: 'WorkflowAPI', ...request });
        const params = new URLSearchParams({
            playlist_id: request.playlist_id,
            source: request.source,
        });

        if (request.mood_prompt) {
            params.append('mood_prompt', request.mood_prompt);
        }

        return this.request<StartRecommendationResponse>(
            `/api/agents/recommendations/remix?${params.toString()}`,
            {
                method: 'POST',
            }
        );
    }

    async getWorkflowStatus(sessionId: string): Promise<WorkflowStatus> {
        return this.request<WorkflowStatus>(`/api/agents/recommendations/${sessionId}/status`);
    }

    /**
     * Get the SSE stream URL for a workflow session
     * Use this with EventSource for real-time updates
     */
    getStreamUrl(sessionId: string): string {
        return `${config.api.baseUrl}/api/agents/recommendations/${sessionId}/stream`;
    }

    async getWorkflowResults(sessionId: string): Promise<WorkflowResults> {
        return this.request<WorkflowResults>(`/api/agents/recommendations/${sessionId}/results`);
    }

    async getPlaylistDetails(sessionId: string): Promise<PlaylistDetails> {
        return this.request<PlaylistDetails>(`/api/agents/recommendations/${sessionId}/playlist`);
    }

    async getWorkflowCost(sessionId: string): Promise<WorkflowCostSummary> {
        return this.request<WorkflowCostSummary>(`/api/agents/recommendations/${sessionId}/cost`);
    }

    async saveToSpotify(sessionId: string): Promise<{
        session_id: string;
        playlist_id: string;
        playlist_name: string;
        spotify_url?: string;
        spotify_uri?: string;
        tracks_added: number;
        message: string;
        already_saved?: boolean;
    }> {
        return this.request(`/api/playlists/${sessionId}/save-to-spotify`, {
            method: 'POST',
        });
    }

    async syncFromSpotify(sessionId: string): Promise<{
        session_id: string;
        synced: boolean;
        message?: string;
        changes?: {
            tracks_before: number;
            tracks_after: number;
            tracks_added: number;
            tracks_removed: number;
        };
        cover_upload_retry?: {
            attempted: boolean;
            success: boolean;
            message: string;
        };
        recommendations?: Array<{
            track_id: string;
            track_name: string;
            artists: string[];
            spotify_uri?: string;
            confidence_score: number;
            reasoning: string;
            source: string;
        }>;
        playlist_data?: {
            id: string;
            name: string;
            spotify_url?: string;
            [key: string]: unknown;
        };
    }> {
        return this.request(`/api/playlists/${sessionId}/sync-from-spotify`, {
            method: 'POST',
        });
    }

    async cancelWorkflow(sessionId: string): Promise<{
        session_id: string;
        status: string;
        message: string;
    }> {
        return this.request(`/api/agents/recommendations/${sessionId}`, {
            method: 'DELETE',
        });
    }

    async applyCompletedPlaylistEdit(
        sessionId: string,
        editType: 'reorder' | 'remove' | 'add',
        options: {
            trackId?: string;
            newPosition?: number;
            trackUri?: string;
        }
    ): Promise<{
        session_id: string;
        status: string;
        edit_type: string;
        recommendation_count: number;
        message: string;
    }> {
        const params = new URLSearchParams({
            edit_type: editType,
        });

        if (options.trackId) params.append('track_id', options.trackId);
        if (options.newPosition !== undefined) params.append('new_position', options.newPosition.toString());
        if (options.trackUri) params.append('track_uri', options.trackUri);

        return this.request(`/api/playlists/${sessionId}/edit?${params.toString()}`, {
            method: 'POST',
        });
    }

    async searchTracks(query: string, limit: number = 20): Promise<{
        tracks: Array<{
            track_id: string;
            track_name: string;
            artists: string[];
            spotify_uri: string;
            album: string;
            album_image?: string;
            duration_ms: number;
            preview_url?: string;
        }>;
        total: number;
        query: string;
    }> {
        const params = new URLSearchParams({
            query,
            limit: limit.toString(),
        });

        return this.request(`/api/spotify/search/tracks?${params.toString()}`);
    }
}

export const workflowAPI = new WorkflowAPI();
