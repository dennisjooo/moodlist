'use client';

import { usePathname } from 'next/navigation';
import { createContext, useContext, useEffect } from 'react';
import { useWorkflowActions, useWorkflowSSE, useWorkflowState } from '../hooks/workflow';
import { WorkflowContextType, WorkflowProviderProps } from '../types/workflow';
import { shouldStreamWorkflow } from '../utils/workflow';

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export function WorkflowProvider({ children }: WorkflowProviderProps) {
  const pathname = usePathname();

  // Use extracted hooks for state management and actions
  const {
    workflowState,
    handleStatusUpdate,
    handleTerminalUpdate,
    handleError,
    handleAwaitingInput,
    setLoading,
    setWorkflowData,
    resetWorkflow,
    clearError,
  } = useWorkflowState();

  const {
    startWorkflow,
    loadWorkflow,
    stopWorkflow,
    refreshResults,
    saveToSpotify,
    syncFromSpotify,
    applyCompletedEdit,
    searchTracks,
  } = useWorkflowActions({
    workflowState,
    setLoading,
    setWorkflowData,
  });

  // Only stream when on /create/[id] pages
  const shouldStream = shouldStreamWorkflow(pathname, workflowState.sessionId);

  // Use the SSE hook with callbacks (falls back to polling if SSE not supported)
  // Cast to satisfy type - 'started' is a valid transient status
  useWorkflowSSE(
    workflowState.sessionId,
    workflowState.status === 'started' ? 'pending' : workflowState.status,
    {
      enabled: shouldStream,
      callbacks: {
        onStatus: handleStatusUpdate,
        onTerminal: handleTerminalUpdate,
        onError: handleError,
        onAwaitingInput: handleAwaitingInput,
      },
    });

  // Clear workflow state when user logs out
  useEffect(() => {
    const handleLogout = () => {
      // Clear workflow state when user logs out
      resetWorkflow();
    };

    window.addEventListener('auth-logout', handleLogout);
    return () => {
      window.removeEventListener('auth-logout', handleLogout);
    };
  }, [resetWorkflow]);

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
        loadWorkflow(sessionId).catch(error => {
          console.error('Failed to load workflow', error);
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, workflowState.sessionId, workflowState.status, workflowState.isLoading]);

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