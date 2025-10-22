'use client';

import { logger } from '@/lib/utils/logger';
import { usePathname } from 'next/navigation';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { WorkflowResults, WorkflowStatus } from '../api/workflow';
import { useWorkflowApi } from '../hooks/useWorkflowApi';
import { useWorkflowPolling } from '../hooks/useWorkflowPolling';
import { WorkflowState, WorkflowContextType, WorkflowProviderProps } from '../types/workflow';

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export function WorkflowProvider({ children }: WorkflowProviderProps) {
  const pathname = usePathname();
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const api = useWorkflowApi();

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

  // Only poll when on /create/[id] pages
  const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
  const shouldPoll = Boolean(workflowState.sessionId && isCreatePage);

  // Use the polling hook with callbacks
  // Cast to satisfy type - 'started' is a valid transient status
  useWorkflowPolling(
    workflowState.sessionId,
    workflowState.status === 'started' ? 'pending' : workflowState.status,
    {
      enabled: shouldPoll,
      callbacks: {
        onStatus: async (status: WorkflowStatus) => {
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
        },
        onTerminal: async (status: WorkflowStatus, results: WorkflowResults | null) => {
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
        },
        onError: (error: Error) => {
          logger.error('Workflow polling error', error, { component: 'WorkflowContext', sessionId: workflowState.sessionId });
          setWorkflowState(prev => ({
            ...prev,
            error: 'Connection error. Please check your internet connection.',
          }));
        },
        onAwaitingInput: () => {
          logger.debug('Workflow awaiting user input', { component: 'WorkflowContext', sessionId: workflowState.sessionId });
        },
      },
    });

  const startWorkflow = async (moodPrompt: string, genreHint?: string) => {
    setWorkflowState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
      moodPrompt,
    }));

    try {
      const response = await api.startWorkflow(moodPrompt, genreHint);

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
      const status = await api.loadWorkflowStatus(sessionId);

      // Only load results if workflow is in terminal state (completed or failed)
      let results = null;
      const isTerminal = status.status === 'completed' || status.status === 'failed';
      if (isTerminal) {
        logger.debug('Workflow is terminal, loading results', { component: 'WorkflowContext', sessionId });
        try {
          results = await api.loadWorkflowResults(sessionId);
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
    // Polling is handled by the hook, just reset state
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
      const results = await api.loadWorkflowResults(workflowState.sessionId);
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
      const result = await api.saveToSpotify(workflowState.sessionId);

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
      const result = await api.syncFromSpotify(workflowState.sessionId);

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
      await api.applyEdit(workflowState.sessionId, editType, options);

      // Use a debounced refresh to prevent race conditions from concurrent edits
      // This ensures only the latest edit triggers a state refresh
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }

      refreshTimeoutRef.current = setTimeout(async () => {
        try {
          if (!workflowState.sessionId) return;
          const results = await api.loadWorkflowResults(workflowState.sessionId);
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
      return await api.searchTracks(query, limit);
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
