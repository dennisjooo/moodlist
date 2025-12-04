import type { ReactNode } from 'react';
import type { WorkflowResults, WorkflowStatus } from '../api/workflow';

// Track type alias matching the structure from WorkflowResults
export type Track = {
    track_id: string;
    track_name: string;
    artists: string[];
    spotify_uri?: string;
    confidence_score: number;
    reasoning: string;
    source: string;
};

// Search result track type (from Spotify search API)
export type SearchTrack = {
    track_id: string;
    track_name: string;
    artists: string[];
    spotify_uri: string;
    album: string;
    album_image?: string;
    duration_ms: number;
    preview_url?: string;
};

export interface AnchorTrack {
    id: string;
    name: string;
    artists: string[];
    album?: string;
    albumName?: string;
    albumCoverUrl?: string;
    user_mentioned?: boolean;
    user_mentioned_artist?: boolean;
    anchor_type?: 'user' | 'genre';
    protected?: boolean;
}

export interface WorkflowState {
    sessionId: string | null;
    status: WorkflowStatus['status'] | 'started' | null;
    currentStep: string;
    moodPrompt: string;
    moodAnalysis?: WorkflowResults['mood_analysis'];
    recommendations: WorkflowResults['recommendations'];
    anchorTracks?: AnchorTrack[];
    playlist?: WorkflowResults['playlist'];
    error: string | null;
    isLoading: boolean;
    awaitingInput: boolean;
    totalLLMCost?: number;
    totalPromptTokens?: number;
    totalCompletionTokens?: number;
    totalTokens?: number;
    metadata?: {
        iteration?: number;
        cohesion_score?: number;
        ordering_strategy?: {
            strategy?: string;
            reasoning?: string;
            phase_distribution?: Record<string, number>;
        };
    };
}

export interface WorkflowContextType {
    workflowState: WorkflowState;
    startWorkflow: (moodPrompt: string, genreHint?: string) => Promise<void>;
    startRemix: (playlistId: string, source: string, moodPrompt?: string) => Promise<any>;
    loadWorkflow: (sessionId: string) => Promise<void>;
    loadWorkflowCost: (sessionId: string) => Promise<void>;
    stopWorkflow: () => void;
    resetWorkflow: () => void;
    applyCompletedEdit: (
        editType: 'reorder' | 'remove' | 'add',
        options: {
            trackId?: string;
            newPosition?: number;
            trackUri?: string;
        }
    ) => Promise<void>;
    searchTracks: (query: string, limit?: number) => Promise<{ tracks: SearchTrack[]; total: number; query: string }>;
    refreshResults: () => Promise<void>;
    saveToSpotify: () => Promise<{
        session_id: string;
        playlist_id: string;
        playlist_name: string;
        spotify_url?: string;
        spotify_uri?: string;
        tracks_added: number;
        message: string;
        already_saved?: boolean;
    }>;
    syncFromSpotify: () => Promise<{
        synced: boolean;
        message?: string;
        changes?: { tracks_added: number; tracks_removed: number };
        cover_upload_retry?: { attempted: boolean; success: boolean; message: string };
    }>;
    clearError: () => void;
}

export interface WorkflowProviderProps {
    children: ReactNode;
}
