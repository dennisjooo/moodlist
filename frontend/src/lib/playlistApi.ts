// API client for playlist-related endpoints

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

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
    created_at: string;
    updated_at: string;
}

export interface UserPlaylistsResponse {
    playlists: UserPlaylist[];
    total: number;
    limit: number;
    offset: number;
}

class PlaylistAPI {
    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${API_BASE_URL}${endpoint}`;

        const config: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            credentials: 'include',
            ...options,
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    async getUserPlaylists(limit: number = 50, offset: number = 0, status?: string): Promise<UserPlaylistsResponse> {
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString(),
        });
        if (status) {
            params.append('status', status);
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

