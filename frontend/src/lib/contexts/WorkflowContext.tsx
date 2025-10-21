'use client';

import { logger } from '@/lib/utils/logger';
import { usePathname } from 'next/navigation';
import { createContext, ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { pollingManager } from '../pollingManager';
import { workflowAPI, WorkflowResults, WorkflowStatus } from '../workflowApi';

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

export interface WorkflowState {
  sessionId: string | null;
  status: WorkflowStatus['status'] | 'started' | null;
  currentStep: string;
  moodPrompt: string;
  moodAnalysis?: WorkflowResults['mood_analysis'];
  recommendations: WorkflowResults['recommendations'];
  playlist?: WorkflowResults['playlist'];
  error: string | null;
  isLoading: boolean;
  awaitingInput: boolean;
  metadata?: {
    iteration?: number;
    cohesion_score?: number;
  };
}

interface WorkflowContextType {
  workflowState: WorkflowState;
  startWorkflow: (moodPrompt: string, genreHint?: string) => Promise<void>;
  loadWorkflow: (sessionId: string) => Promise<void>;
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
  syncFromSpotify: () => Promise<{ synced: boolean; message?: string; changes?: { tracks_added: number; tracks_removed: number } }>;
  clearError: () => void;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

interface WorkflowProviderProps {
  children: ReactNode;
}

export function WorkflowProvider({ children }: WorkflowProviderProps) {
  const pathname = usePathname();
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    sessionId: null,
    status: null,
    currentStep: '',
    moodPrompt: '',
    moodAnalysis: undefined,
    recommendations: [],
    error: null,
    isLoading: false,
    awaitingInput: false,
  });

  const startWorkflow = async (moodPrompt: string, genreHint?: string) => {
    setWorkflowState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
      moodPrompt,
    }));

    try {
      // Backend will use the authenticated user's tokens automatically
      const response = await workflowAPI.startWorkflow({
        mood_prompt: `${moodPrompt} ${genreHint ? `in the genre of ${genreHint}` : ''}`.trim(),
      });

      setWorkflowState(prev => ({
        ...prev,
        sessionId: response.session_id,
        status: response.status,
        isLoading: true, // Keep loading true so redirect happens
      }));

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start workflow';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      throw error;
    }
  };

  const loadWorkflow = async (sessionId: string) => {
    logger.debug('[loadWorkflow] Called', {
      component: 'WorkflowContext',
      sessionId,
      state: {
        sessionId: workflowState.sessionId,
        status: workflowState.status,
        isLoading: workflowState.isLoading,
      }
    });

    // Prevent concurrent calls
    if (workflowState.isLoading) {
      logger.debug('[loadWorkflow] Already loading, skipping duplicate call', { component: 'WorkflowContext' });
      return;
    }

    // If we already have this session loaded and it's terminal, no need to reload
    if (workflowState.sessionId === sessionId &&
      (workflowState.status === 'completed' || workflowState.status === 'failed') &&
      workflowState.recommendations.length > 0) {
      logger.debug('[loadWorkflow] Already loaded and terminal, skipping', { component: 'WorkflowContext', sessionId });
      return;
    }

    logger.debug('[loadWorkflow] Proceeding with API calls', { component: 'WorkflowContext', sessionId });
    setWorkflowState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      logger.debug('[loadWorkflow] Fetching status', { component: 'WorkflowContext', sessionId });
      // Load workflow status once
      const status = await workflowAPI.getWorkflowStatus(sessionId);

      // Only load results if workflow is in terminal state (completed or failed)
      let results = null;
      const isTerminal = status.status === 'completed' || status.status === 'failed';
      if (isTerminal) {
        logger.debug('Workflow is terminal, loading results', { component: 'WorkflowContext', sessionId });
        try {
          results = await workflowAPI.getWorkflowResults(sessionId);
        } catch {
          // Results might not be ready yet, that's ok
          logger.warn('Results not ready yet for terminal workflow', { component: 'WorkflowContext', sessionId });
        }
      } else {
        logger.debug('Workflow is active', { component: 'WorkflowContext', status: status.status, sessionId });
      }

      setWorkflowState(prev => ({
        ...prev,
        sessionId: status.session_id,
        status: status.status,
        currentStep: status.current_step,
        moodPrompt: status.mood_prompt,
        moodAnalysis: results?.mood_analysis,
        recommendations: results?.recommendations || [],
        playlist: results?.playlist,
        awaitingInput: status.awaiting_input,
        error: status.error || null,
        isLoading: false,
      }));

      logger.info('Workflow loaded', { component: 'WorkflowContext', sessionId, status: status.status });

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load workflow';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      logger.error('Failed to load workflow for session', error, { component: 'WorkflowContext', sessionId });
    }
  };

  const stopWorkflow = () => {
    // Stop polling immediately if there's an active session
    if (workflowState.sessionId) {
      pollingManager.stopPolling(workflowState.sessionId);
    }

    // Don't clear auth state, just reset workflow state
    setWorkflowState({
      sessionId: null,
      status: null,
      currentStep: '',
      moodPrompt: '',
      moodAnalysis: undefined,
      recommendations: [],
      error: null,
      isLoading: false,
      awaitingInput: false,
    });
  };

  const resetWorkflow = () => {
    logger.debug('Resetting workflow state, preserving auth', { component: 'WorkflowContext' });
    // Reset workflow state to start fresh while preserving auth
    setWorkflowState({
      sessionId: null,
      status: null,
      currentStep: '',
      moodPrompt: '',
      moodAnalysis: undefined,
      recommendations: [],
      error: null,
      isLoading: false,
      awaitingInput: false,
    });
  };

  const refreshResults = async () => {
    if (!workflowState.sessionId) return;

    // Don't fetch results if we're already in a terminal state and have results
    if ((workflowState.status === 'completed' || workflowState.status === 'failed') &&
      workflowState.recommendations.length > 0) {
      logger.debug('Results already loaded for terminal workflow, skipping refresh', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      return;
    }

    logger.debug('Fetching results', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
    setWorkflowState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const results = await workflowAPI.getWorkflowResults(workflowState.sessionId);
      setWorkflowState(prev => ({
        ...prev,
        recommendations: results.recommendations,
        playlist: results.playlist,
        isLoading: false,
      }));
      logger.info('Results fetched successfully', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh results';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      logger.error('Failed to fetch results', error, { component: 'WorkflowContext', sessionId: workflowState.sessionId });
    }
  };

  const saveToSpotify = async () => {
    if (!workflowState.sessionId) {
      throw new Error('No active workflow session');
    }

    setWorkflowState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await workflowAPI.saveToSpotify(workflowState.sessionId);

      // Update state with playlist information
      setWorkflowState(prev => ({
        ...prev,
        playlist: {
          id: result.playlist_id,
          name: result.playlist_name,
          spotify_url: result.spotify_url,
          spotify_uri: result.spotify_uri,
        },
        isLoading: false,
      }));

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save playlist to Spotify';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      throw error;
    }
  };

  const syncFromSpotify = async () => {
    if (!workflowState.sessionId) {
      throw new Error('No active workflow session');
    }

    // Don't show loading state for sync - it should be subtle
    try {
      const result = await workflowAPI.syncFromSpotify(workflowState.sessionId);

      // Only update if sync was successful
      if (result.synced && result.recommendations) {
        setWorkflowState(prev => ({
          ...prev,
          recommendations: result.recommendations || prev.recommendations,
          playlist: result.playlist_data ? {
            ...prev.playlist,
            ...result.playlist_data,
          } : prev.playlist,
        }));
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to sync from Spotify';
      logger.error('Sync error', error, { component: 'WorkflowContext', errorMessage });
      // Don't set error in state for sync failures - they should be silent or handled by caller
      throw error;
    }
  };

  const applyCompletedEdit = async (
    editType: 'reorder' | 'remove' | 'add',
    options: {
      trackId?: string;
      newPosition?: number;
      trackUri?: string;
    }
  ) => {
    if (!workflowState.sessionId) {
      throw new Error('No active workflow session');
    }

    // Don't set loading state - let the component handle optimistic updates
    try {
      await workflowAPI.applyCompletedPlaylistEdit(workflowState.sessionId, editType, options);

      // Use a debounced refresh to prevent race conditions from concurrent edits
      // This ensures only the latest edit triggers a state refresh
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }

      refreshTimeoutRef.current = setTimeout(async () => {
        try {
          if (!workflowState.sessionId) return;
          const results = await workflowAPI.getWorkflowResults(workflowState.sessionId);
          setWorkflowState(prev => ({
            ...prev,
            recommendations: results.recommendations,
            playlist: results.playlist,
          }));
        } catch (error) {
          logger.error('Failed to refresh workflow results after edit', error, { component: 'WorkflowContext' });
        }
      }, 100); // 100ms debounce to batch concurrent edits
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to apply edit';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const searchTracks = async (query: string, limit: number = 20) => {
    try {
      return await workflowAPI.searchTracks(query, limit);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to search tracks';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
      }));
      throw error;
    }
  };

  const clearError = () => {
    setWorkflowState(prev => ({ ...prev, error: null }));
  };

  // Clear workflow state when user logs out
  useEffect(() => {
    const handleLogout = () => {
      // Clear workflow state when user logs out
      setWorkflowState({
        sessionId: null,
        status: null,
        currentStep: '',
        moodPrompt: '',
        recommendations: [],
        error: null,
        isLoading: false,
        awaitingInput: false,
      });
    };

    window.addEventListener('auth-logout', handleLogout);
    return () => {
      window.removeEventListener('auth-logout', handleLogout);
    };
  }, []);

  // Handle pathname changes - load workflow when navigating to create pages
  useEffect(() => {
    // Check if we're on a create page and need to load a workflow
    const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    if (isCreatePage) {
      const sessionId = pathname.split('/')[2];
      // Only load if: different session OR (same session but no status loaded yet and not currently loading)
      const needsLoad = sessionId && (
        (workflowState.sessionId !== sessionId && !workflowState.isLoading) ||
        (workflowState.sessionId === sessionId && workflowState.status === null && !workflowState.isLoading)
      );
      if (needsLoad) {
        logger.info('Loading workflow for page navigation', { component: 'WorkflowContext', sessionId });
        loadWorkflow(sessionId).catch(error => {
          logger.error('Failed to load workflow', error, { component: 'WorkflowContext', sessionId });
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, workflowState.sessionId, workflowState.status, workflowState.isLoading]);

  // Auto-refresh workflow status when there's an active session
  useEffect(() => {
    // Don't poll if no session
    if (!workflowState.sessionId) {
      return;
    }

    // Only poll when on /create/[id] pages
    const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    if (!isCreatePage) {
      logger.debug('Not on create page, stopping polling', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      pollingManager.stopPolling(workflowState.sessionId);
      return;
    }

    // Check if workflow is in a terminal state - if so, stop any polling and don't start new
    const isTerminalState = workflowState.status === 'completed' || workflowState.status === 'failed';
    if (isTerminalState) {
      logger.debug('Workflow in terminal state, stopping polling', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      pollingManager.stopPolling(workflowState.sessionId);
      return;
    }

    const pollWorkflow = async () => {
      return await workflowAPI.getWorkflowStatus(workflowState.sessionId!);
    };

    const handleStatus = async (status: WorkflowStatus) => {
      // If workflow reached terminal state, stop polling immediately and update state
      const isTerminal = status.status === 'completed' || status.status === 'failed';

      if (isTerminal) {
        // Stop polling immediately when terminal state is detected
        logger.debug('Terminal state detected, stopping polling', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
        pollingManager.stopPolling(workflowState.sessionId!);

        // Fetch results when workflow completes
        let results = null;
        try {
          logger.debug('Fetching results for completed workflow', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
          results = await workflowAPI.getWorkflowResults(workflowState.sessionId!);
        } catch (e) {
          logger.error('Failed to fetch results for completed workflow', e, { component: 'WorkflowContext', sessionId: workflowState.sessionId });
        }

        // Update state with terminal status and results
        setWorkflowState(prev => ({
          ...prev,
          status: status.status,
          currentStep: status.current_step,
          awaitingInput: status.awaiting_input,
          error: status.error || null,
          moodAnalysis: results?.mood_analysis || prev.moodAnalysis,
          recommendations: results?.recommendations || prev.recommendations,
          playlist: results?.playlist || prev.playlist,
        }));

        logger.info('Terminal state set with results, polling stopped', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      } else {
        // For non-terminal states, just update the status
        setWorkflowState(prev => ({
          ...prev,
          status: status.status,
          currentStep: status.current_step,
          awaitingInput: status.awaiting_input,
          error: status.error || null,
          moodAnalysis: status.mood_analysis || prev.moodAnalysis,
          metadata: status.metadata || prev.metadata,
        }));
      }
    };

    const handleError = (error: Error) => {
      logger.error('Workflow polling error', error, { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      // Set error state for persistent errors
      setWorkflowState(prev => ({
        ...prev,
        error: 'Connection error. Please check your internet connection.',
      }));
    };

    const handleAwaitingInput = () => {
      // Optional: Handle when workflow is waiting for user input
      logger.debug('Workflow awaiting user input', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
    };

    logger.debug('Starting polling', { component: 'WorkflowContext', sessionId: workflowState.sessionId, status: workflowState.status });
    pollingManager.startPolling(
      workflowState.sessionId,
      pollWorkflow,
      {
        onStatus: handleStatus,
        onError: handleError,
        onAwaitingInput: handleAwaitingInput,
      }
    );

    // Double-check that polling starts with correct state
    logger.debug('Polling started', { component: 'WorkflowContext', sessionId: workflowState.sessionId });

    return () => {
      logger.debug('Cleanup: stopping polling', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
      pollingManager.stopPolling(workflowState.sessionId!);
    };
  }, [workflowState.sessionId, workflowState.status, pathname]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

  const value: WorkflowContextType = {
    workflowState,
    startWorkflow,
    loadWorkflow,
    stopWorkflow,
    resetWorkflow,
    applyCompletedEdit,
    searchTracks,
    refreshResults,
    saveToSpotify,
    syncFromSpotify,
    clearError,
  };

  return (
    <WorkflowContext.Provider value={value}>
      {children}
    </WorkflowContext.Provider>
  );
}

export function useWorkflow() {
  const context = useContext(WorkflowContext);
  if (context === undefined) {
    throw new Error('useWorkflow must be used within a WorkflowProvider');
  }
  return context;
}