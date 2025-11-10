// API client for Spotify-related endpoints

import { AxiosError, AxiosRequestConfig, isAxiosError } from 'axios';

import apiClient from '@/lib/axios';
import { logger } from '@/lib/utils/logger';

export interface SpotifyProfile {
    id: string;
    display_name: string;
    email?: string;
    images: Array<{ url: string; height: number; width: number }>;
    country?: string;
    followers: number;
}

export interface TrackDetails {
    track_id: string;
    track_name: string;
    artists: Array<{ name: string; id: string }>;
    album: {
        name: string;
        id: string;
        release_date: string;
        total_tracks: number;
        images: Array<{ url: string; height: number; width: number }>;
    };
    album_image?: string;
    duration_ms: number;
    explicit: boolean;
    popularity: number;
    preview_url?: string;
    spotify_uri: string;
    spotify_url?: string;
    track_number: number;
    disc_number: number;
}

class SpotifyAPI {
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

                logger.error('Spotify API request failed', error, {
                    component: 'SpotifyAPI',
                    status,
                    statusText,
                    endpoint,
                });

                throw new Error(`API request failed: ${status} ${statusText}`);
            }

            logger.error('Unexpected Spotify API error', error, {
                component: 'SpotifyAPI',
                endpoint,
            });
            throw error;
        }
    }

    async getProfile(): Promise<SpotifyProfile> {
        return this.request<SpotifyProfile>('/api/spotify/profile');
    }

    async getTrackDetails(trackUri: string): Promise<TrackDetails> {
        return this.request<TrackDetails>(`/api/spotify/tracks/${encodeURIComponent(trackUri)}`);
    }
}

export const spotifyAPI = new SpotifyAPI();

