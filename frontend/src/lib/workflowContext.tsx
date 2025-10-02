'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from './authContext';
import { workflowAPI, WorkflowStatus, WorkflowResults, PlaylistEditRequest } from './workflowApi';
import { pollingManager } from './pollingManager';

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
}

interface WorkflowContextType {
  workflowState: WorkflowState;
  startWorkflow: (moodPrompt: string, genreHint?: string) => Promise<void>;
  loadWorkflow: (sessionId: string) => Promise<void>;
  stopWorkflow: () => void;
  resetWorkflow: () => void;
  applyEdit: (edit: PlaylistEditRequest) => Promise<void>;
  refreshResults: () => Promise<void>;
  saveToSpotify: () => Promise<any>;
  clearError: () => void;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

interface WorkflowProviderProps {
  children: ReactNode;
}

export function WorkflowProvider({ children }: WorkflowProviderProps) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const pathname = usePathname();

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
    // Wait for authentication verification to complete if it's still loading
    if (authLoading) {
      console.log('Auth still loading, waiting for verification to complete...');
      // Wait for auth loading to complete
      await new Promise<void>((resolve) => {
        const checkAuth = () => {
          if (!authLoading) {
            resolve();
          } else {
            setTimeout(checkAuth, 50);
          }
        };
        checkAuth();
      });
    }

    if (!isAuthenticated || !user) {
      throw new Error('User must be authenticated to start workflow');
    }

    setWorkflowState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
      moodPrompt,
    }));

    try {
      // Backend will use the authenticated user's tokens automatically
      const response = await workflowAPI.startWorkflow({
        mood_prompt: `${moodPrompt} ${genreHint ? `in the genre of ${genreHint}` : ''}`,
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
    console.log('[loadWorkflow] Called with sessionId:', sessionId, 'current state:', {
      sessionId: workflowState.sessionId,
      status: workflowState.status,
      isLoading: workflowState.isLoading,
    });

    // Prevent concurrent calls
    if (workflowState.isLoading) {
      console.log('[loadWorkflow] Already loading, skipping duplicate call');
      return;
    }

    // If auth is still loading, defer the load - the useEffect will retry when ready
    if (authLoading) {
      console.log('[loadWorkflow] Auth still loading, deferring');
      return;
    }

    if (!isAuthenticated || !user) {
      console.log('[loadWorkflow] User not authenticated');
      setWorkflowState(prev => ({
        ...prev,
        error: 'Please log in to view this session',
        isLoading: false,
      }));
      return;
    }

    // If we already have this session loaded and it's terminal, no need to reload
    if (workflowState.sessionId === sessionId &&
      (workflowState.status === 'completed' || workflowState.status === 'failed') &&
      workflowState.recommendations.length > 0) {
      console.log('[loadWorkflow] Already loaded and terminal, skipping');
      return;
    }

    console.log('[loadWorkflow] Proceeding with API calls');
    setWorkflowState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      console.log('[loadWorkflow] Fetching status for session:', sessionId);
      // Load workflow status once
      const status = await workflowAPI.getWorkflowStatus(sessionId);

      // Only load results if workflow is in terminal state (completed or failed)
      let results = null;
      const isTerminal = status.status === 'completed' || status.status === 'failed';
      if (isTerminal) {
        console.log('Workflow is terminal, loading results for session:', sessionId);
        try {
          results = await workflowAPI.getWorkflowResults(sessionId);
        } catch (e) {
          // Results might not be ready yet, that's ok
          console.log('Results not ready yet for terminal workflow:', e);
        }
      } else {
        console.log('Workflow is active, status:', status.status, 'for session:', sessionId);
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

      console.log('Workflow loaded successfully for session:', sessionId, 'status:', status.status);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load workflow';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      console.error('Failed to load workflow for session:', sessionId, error);
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
    console.log('Resetting workflow state, preserving auth');
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

  const applyEdit = async (edit: PlaylistEditRequest) => {
    if (!workflowState.sessionId) {
      throw new Error('No active workflow session');
    }

    setWorkflowState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await workflowAPI.applyPlaylistEdit(workflowState.sessionId, edit);
      // Refresh the workflow state after edit
      await refreshResults();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to apply edit';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      throw error;
    }
  };

  const refreshResults = async () => {
    if (!workflowState.sessionId) return;

    // Don't fetch results if we're already in a terminal state and have results
    if ((workflowState.status === 'completed' || workflowState.status === 'failed') &&
      workflowState.recommendations.length > 0) {
      console.log('Results already loaded for terminal workflow, skipping refresh');
      return;
    }

    console.log('Fetching results for session:', workflowState.sessionId);
    setWorkflowState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const results = await workflowAPI.getWorkflowResults(workflowState.sessionId);
      setWorkflowState(prev => ({
        ...prev,
        recommendations: results.recommendations,
        playlist: results.playlist,
        isLoading: false,
      }));
      console.log('Results fetched successfully for session:', workflowState.sessionId);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh results';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      console.error('Failed to fetch results for session:', workflowState.sessionId, error);
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

  // Handle auth state changes - retry workflow loading if auth becomes available
  useEffect(() => {
    // If auth was loading and is now complete, and we have a pending workflow load
    if (!authLoading && isAuthenticated && user) {
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
          console.log('Auth verification completed, loading workflow:', sessionId);
          loadWorkflow(sessionId).catch(error => {
            console.error('Failed to load workflow after auth verification:', error);
          });
        }
      }
    }
  }, [authLoading, isAuthenticated, user, pathname, workflowState.sessionId, workflowState.status, workflowState.isLoading]);

  // Auto-refresh workflow status when there's an active session
  useEffect(() => {
    // Don't poll if no session
    if (!workflowState.sessionId) {
      return;
    }

    // Don't poll if auth is still loading
    if (authLoading) {
      console.log('Auth still loading, skipping workflow polling for session:', workflowState.sessionId);
      return;
    }

    // Don't poll if not authenticated
    if (!isAuthenticated || !user) {
      console.log('User not authenticated, skipping workflow polling for session:', workflowState.sessionId);
      return;
    }

    // Only poll when on /create/[id] pages
    const isCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    if (!isCreatePage) {
      console.log('Not on create page, stopping polling for session:', workflowState.sessionId);
      pollingManager.stopPolling(workflowState.sessionId);
      return;
    }

    // Check if workflow is in a terminal state - if so, stop any polling and don't start new
    const isTerminalState = workflowState.status === 'completed' || workflowState.status === 'failed';
    if (isTerminalState) {
      console.log('Workflow in terminal state, stopping polling for session:', workflowState.sessionId);
      pollingManager.stopPolling(workflowState.sessionId);
      return;
    }

    const pollWorkflow = async () => {
      return await workflowAPI.getWorkflowStatus(workflowState.sessionId!);
    };

    const handleStatus = (status: WorkflowStatus) => {
      // If workflow reached terminal state, stop polling immediately and update state
      const isTerminal = status.status === 'completed' || status.status === 'failed';

      if (isTerminal) {
        // Stop polling immediately when terminal state is detected
        console.log('Terminal state detected, stopping polling for session:', workflowState.sessionId);
        pollingManager.stopPolling(workflowState.sessionId!);

        // Update state immediately with terminal status (no additional API calls)
        setWorkflowState(prev => ({
          ...prev,
          status: status.status,
          currentStep: status.current_step,
          awaitingInput: status.awaiting_input,
          error: status.error || null,
        }));

        console.log('Terminal state set, polling stopped for session:', workflowState.sessionId);
      } else {
        // For non-terminal states, just update the status
        setWorkflowState(prev => ({
          ...prev,
          status: status.status,
          currentStep: status.current_step,
          awaitingInput: status.awaiting_input,
          error: status.error || null,
        }));
      }
    };

    const handleError = (error: Error) => {
      console.error('Workflow polling error:', error);
      // Set error state for persistent errors
      setWorkflowState(prev => ({
        ...prev,
        error: 'Connection error. Please check your internet connection.',
      }));
    };

    const handleAwaitingInput = () => {
      // Optional: Handle when workflow is waiting for user input
      console.log('Workflow awaiting user input');
    };

    console.log('Starting polling for session:', workflowState.sessionId, 'status:', workflowState.status);
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
    console.log('Polling started for session:', workflowState.sessionId);

    return () => {
      console.log('Cleanup: stopping polling for session:', workflowState.sessionId);
      pollingManager.stopPolling(workflowState.sessionId!);
    };
  }, [workflowState.sessionId, workflowState.status, pathname, authLoading, isAuthenticated, user]);

  const value: WorkflowContextType = {
    workflowState,
    startWorkflow,
    loadWorkflow,
    stopWorkflow,
    resetWorkflow,
    applyEdit,
    refreshResults,
    saveToSpotify,
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