// API client for playlist-related endpoints

import { config } from '@/lib/config';
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
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${config.api.baseUrl}${endpoint}`;

        const reqConfig: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            credentials: 'include',
            ...options,
        };

        const response = await fetch(url, reqConfig);

        if (!response.ok) {
            logger.error('Playlist API request failed', undefined, { component: 'PlaylistAPI', status: response.status, statusText: response.statusText, endpoint });
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return await response.json();
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

