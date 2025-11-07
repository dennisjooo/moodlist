// API client for playlist-related endpoints

import { AxiosError, AxiosRequestConfig, isAxiosError } from 'axios';

import apiClient from '@/lib/axios';
import { logger } from '@/lib/utils/logger';

export interface MoodAnalysis {
    mood_interpretation?: string;
    primary_emotion?: string;
    energy_level?: string;
    target_features?: Record<string, [number, number]>;
    feature_weights?: Record<string, number>;
    search_keywords?: string[];
    artist_recommendations?: string[];
    genre_keywords?: string[];
    reasoning?: string;
    color_scheme?: {
        primary: string;
        secondary: string;
        tertiary: string;
    };
}

export interface UserPlaylist {
    id: number;
    session_id: string;
    mood_prompt: string;
    name?: string;
    status: string;
    track_count: number;
    spotify_url?: string;
    spotify_uri?: string;
    spotify_playlist_id?: string;
    mood_analysis_data?: MoodAnalysis;

    // LLM-generated triadic color scheme
    color_primary?: string;
    color_secondary?: string;
    color_tertiary?: string;

    created_at: string;
    updated_at: string;
}

export interface UserPlaylistsResponse {
    playlists: UserPlaylist[];
    total: number;
    limit: number;
    offset: number;
    sort_by?: 'created_at' | 'name' | 'track_count';
    sort_order?: 'asc' | 'desc';
    search?: string | null;
}

class PlaylistAPI {
    private async request<T>(
        endpoint: string,
        options: AxiosRequestConfig = {}
    ): Promise<T> {
        try {
            const response = await apiClient.request<T>({
                url: endpoint,
                ...options,
            });

            return response.data;
        } catch (error) {
            if (isAxiosError(error)) {
                const axiosError = error as AxiosError;
                const status = axiosError.response?.status ?? 0;
                const statusText = axiosError.response?.statusText ?? axiosError.message;

                logger.error('Playlist API request failed', error, {
                    component: 'PlaylistAPI',
                    status,
                    statusText,
                    endpoint,
                });

                throw new Error(`API request failed: ${status} ${statusText}`);
            }

            logger.error('Unexpected Playlist API error', error, {
                component: 'PlaylistAPI',
                endpoint,
            });
            throw error;
        }
    }

    async getUserPlaylists(
        limit: number = 50,
        offset: number = 0,
        excludeStatuses?: string[],
        search?: string,
        sortBy?: 'created_at' | 'name' | 'track_count',
        sortOrder?: 'asc' | 'desc',
    ): Promise<UserPlaylistsResponse> {
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString(),
        });
        if (excludeStatuses && excludeStatuses.length > 0) {
            params.append('exclude_statuses', excludeStatuses.join(','));
        }
        if (search) {
            params.append('search', search);
        }
        if (sortBy) {
            params.append('sort_by', sortBy);
        }
        if (sortOrder) {
            params.append('sort_order', sortOrder);
        }
        return this.request<UserPlaylistsResponse>(
            `/api/playlists?${params.toString()}`
        );
    }

    async getPlaylist(playlistId: number): Promise<UserPlaylist> {
        return this.request<UserPlaylist>(`/api/playlists/${playlistId}`);
    }

    async getPlaylistBySession(sessionId: string): Promise<UserPlaylist> {
        return this.request<UserPlaylist>(`/api/playlists/session/${sessionId}`);
    }

    async deletePlaylist(playlistId: number): Promise<{ message: string; playlist_id: number }> {
        return this.request(`/api/playlists/${playlistId}`, {
            method: 'DELETE',
        });
    }

    async getPlaylistStats(): Promise<{
        total_playlists: number;
        completed_playlists: number;
        total_tracks: number;
        user_id: number;
    }> {
        return this.request(`/api/playlists/stats/summary`);
    }
}

export const playlistAPI = new PlaylistAPI();

