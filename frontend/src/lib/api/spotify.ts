// API client for Spotify-related endpoints

import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

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
            logger.error('Spotify API request failed', undefined, {
                component: 'SpotifyAPI',
                status: response.status,
                statusText: response.statusText,
                endpoint,
            });
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    async getTrackDetails(trackId: string): Promise<TrackDetails> {
        return this.request<TrackDetails>(`/api/spotify/tracks/${trackId}`);
    }
}

export const spotifyAPI = new SpotifyAPI();

