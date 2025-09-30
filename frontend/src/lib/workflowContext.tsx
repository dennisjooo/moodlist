'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useAuth } from './authContext';
import { workflowAPI, WorkflowStatus, WorkflowResults, PlaylistEditRequest } from './workflowApi';
import { pollingManager } from './pollingManager';

export interface WorkflowState {
  sessionId: string | null;
  status: WorkflowStatus['status'] | 'started' | null;
  currentStep: string;
  moodPrompt: string;
  recommendations: WorkflowResults['recommendations'];
  playlist?: WorkflowResults['playlist'];
  error: string | null;
  isLoading: boolean;
  awaitingInput: boolean;
}

interface WorkflowContextType {
  workflowState: WorkflowState;
  startWorkflow: (moodPrompt: string) => Promise<void>;
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
  const { user, isAuthenticated } = useAuth();

  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    sessionId: null,
    status: null,
    currentStep: '',
    moodPrompt: '',
    recommendations: [],
    error: null,
    isLoading: false,
    awaitingInput: false,
  });

  const startWorkflow = async (moodPrompt: string) => {
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
        mood_prompt: moodPrompt,
      });

      setWorkflowState(prev => ({
        ...prev,
        sessionId: response.session_id,
        status: response.status,
        isLoading: false,
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

  const stopWorkflow = () => {
    // Don't clear auth state, just reset workflow state
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

  const resetWorkflow = () => {
    console.log('Resetting workflow state, preserving auth');
    // Reset workflow state to start fresh while preserving auth
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

    setWorkflowState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const results = await workflowAPI.getWorkflowResults(workflowState.sessionId);
      setWorkflowState(prev => ({
        ...prev,
        recommendations: results.recommendations,
        playlist: results.playlist,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh results';
      setWorkflowState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
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

  // Auto-refresh workflow status when there's an active session
  useEffect(() => {
    if (!workflowState.sessionId || workflowState.status === 'completed' || workflowState.status === 'failed') {
      return;
    }

    const pollWorkflow = async () => {
      return await workflowAPI.getWorkflowStatus(workflowState.sessionId!);
    };

    const handleStatus = (status: WorkflowStatus) => {
      setWorkflowState(prev => ({
        ...prev,
        status: status.status,
        currentStep: status.current_step,
        awaitingInput: status.awaiting_input,
        error: status.error || null,
      }));

      // If workflow is completed or failed, get final results
      if (status.status === 'completed' || status.status === 'failed') {
        refreshResults();
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

    pollingManager.startPolling(
      workflowState.sessionId,
      pollWorkflow,
      {
        onStatus: handleStatus,
        onError: handleError,
        onAwaitingInput: handleAwaitingInput,
      }
    );

    return () => {
      pollingManager.stopPolling(workflowState.sessionId!);
    };
  }, [workflowState.sessionId, workflowState.status]);

  const value: WorkflowContextType = {
    workflowState,
    startWorkflow,
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