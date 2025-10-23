// API client for user-related endpoints

import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

export interface UserStats {
    user_id: number;
    saved_playlists: number;
    moods_analyzed: number;
    total_sessions: number;
    active_sessions: number;
    total_tracks: number;
}

export interface RecentPlaylist {
    id: number;
    mood_prompt: string;
    status: string;
    track_count: number;
    created_at: string;
    name?: string;
    spotify_url?: string;
    primary_emotion?: string;
    energy_level?: string;
}

export interface MoodDistribution {
    emotion: string;
    count: number;
}

export interface AudioInsights {
    avg_energy: number;
    avg_valence: number;
    avg_danceability: number;
    energy_distribution: {
        high: number;
        medium: number;
        low: number;
    };
}

export interface StatusBreakdown {
    pending: number;
    completed: number;
    failed: number;
}

export interface DashboardData {
    stats: UserStats;
    recent_activity: RecentPlaylist[];
    mood_distribution: MoodDistribution[];
    audio_insights: AudioInsights;
    status_breakdown: StatusBreakdown;
}

class UserAPI {
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
            logger.error('User API request failed', undefined, {
                component: 'UserAPI',
                status: response.status,
                statusText: response.statusText,
                endpoint
            });
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    async getDashboard(): Promise<DashboardData> {
        return this.request<DashboardData>('/api/auth/dashboard');
    }

    async getUserPlaylists(limit: number = 50, offset: number = 0, status?: string): Promise<RecentPlaylist[]> {
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString(),
        });
        if (status) {
            params.append('status', status);
        }
        const response = await this.request<{ playlists: RecentPlaylist[], total: number, limit: number, offset: number }>(`/api/playlists?${params.toString()}`);
        return response.playlists;
    }
}

export const userAPI = new UserAPI();

