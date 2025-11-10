// API client for user-related endpoints

import { AxiosError, AxiosRequestConfig, isAxiosError } from 'axios';

import apiClient from '@/lib/axios';
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

export interface QuotaStatus {
    used: number;
    limit: number;
    remaining: number;
    can_create: boolean;
}

class UserAPI {
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

                logger.error('User API request failed', error, {
                    component: 'UserAPI',
                    status,
                    statusText,
                    endpoint,
                });

                throw new Error(`API request failed: ${status} ${statusText}`);
            }

            logger.error('Unexpected User API error', error, {
                component: 'UserAPI',
                endpoint,
            });
            throw error;
        }
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

    async getQuotaStatus(): Promise<QuotaStatus> {
        return this.request<QuotaStatus>('/api/auth/quota');
    }
}

export const userAPI = new UserAPI();

