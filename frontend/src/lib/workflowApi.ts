// API service layer for agentic workflow endpoints
// Following the interfaces from FRONTEND_INTEGRATION_GUIDE.md

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

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
  "optimizing_recommendations" | "awaiting_user_input" |
  "processing_edits" | "creating_playlist" |
  "completed" | "failed";
  current_step: string;
  mood_prompt: string;
  mood_analysis?: {
    mood_interpretation: string;
    primary_emotion: string;
    energy_level: string;
    target_features: Record<string, number>;
    search_keywords: string[];
  };
  recommendation_count: number;
  seed_track_count?: number;
  user_top_tracks_count?: number;
  user_top_artists_count?: number;
  has_playlist: boolean;
  awaiting_input: boolean;
  error?: string;
  created_at: string;
  updated_at: string;
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
  metadata: Record<string, any>;
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
  mood_analysis: any;
  total_tracks: number;
  created_at: string;
}

class WorkflowAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'WorkflowAPIError';
  }
}

class WorkflowAPI {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log('Making API request to:', url, 'with credentials:', options.credentials || 'include');

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include',
      ...options,
    };

    try {
      const response = await fetch(url, config);
      console.log('API response status:', response.status, 'for endpoint:', endpoint);

      if (!response.ok) {
        console.error('API request failed:', response.status, response.statusText);
        throw new WorkflowAPIError(
          response.status,
          `API request failed: ${response.status} ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error('API request error for endpoint:', endpoint, error);
      if (error instanceof WorkflowAPIError) {
        throw error;
      }
      throw new WorkflowAPIError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async startWorkflow(request: StartRecommendationRequest): Promise<StartRecommendationResponse> {
    console.log('Starting workflow with mood:', request.mood_prompt);
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

  async getWorkflowStatus(sessionId: string): Promise<WorkflowStatus> {
    return this.request<WorkflowStatus>(`/api/agents/recommendations/${sessionId}/status`);
  }

  async getWorkflowResults(sessionId: string): Promise<WorkflowResults> {
    return this.request<WorkflowResults>(`/api/agents/recommendations/${sessionId}/results`);
  }

  async applyPlaylistEdit(sessionId: string, edit: PlaylistEditRequest): Promise<void> {
    const params = new URLSearchParams({
      edit_type: edit.edit_type,
    });

    if (edit.track_id) params.append('track_id', edit.track_id);
    if (edit.new_position !== undefined) params.append('new_position', edit.new_position.toString());
    if (edit.reasoning) params.append('reasoning', edit.reasoning);

    return this.request<void>(`/api/agents/recommendations/${sessionId}/edit?${params.toString()}`, {
      method: 'POST',
    });
  }

  async getPlaylistDetails(sessionId: string): Promise<PlaylistDetails> {
    return this.request<PlaylistDetails>(`/api/agents/recommendations/${sessionId}/playlist`);
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
    return this.request(`/api/agents/recommendations/${sessionId}/save-to-spotify`, {
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

    return this.request(`/api/agents/recommendations/${sessionId}/edit-completed?${params.toString()}`, {
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