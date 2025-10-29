'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { logger } from '@/lib/utils/logger';
import { useToast } from '../ui/useToast';

/**
 * Custom hook to manage create page logic and state
 * Extracts complex logic from the create page component
 */
export function useCreatePageLogic() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuth();
  const { workflowState, startWorkflow, resetWorkflow } = useWorkflow();
  const toast = useToast();

  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [showLoginDialog, setShowLoginDialog] = useState(false);

  // Get mood from URL params if present
  useEffect(() => {
    const moodParam = searchParams.get('mood');
    if (moodParam) {
      setSelectedMood(moodParam);
    }
  }, [searchParams]);

  // Clear any existing workflow state on mount to start fresh
  // This ensures that when user navigates to /create (e.g., via cancel button),
  // the page shows the initial mood input form
  useEffect(() => {
    // If there's a session ID when mounting /create (not /create/[id]),
    // it means we're coming from a cancelled workflow or navigating back
    // Clear it to show a fresh state
    if (workflowState.sessionId) {
      logger.debug('Clearing workflow state on /create mount', { component: 'CreatePage' });
      resetWorkflow();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Also clear workflow state when it changes while on /create page
  // This handles cases where user stops workflow while already on /create
  useEffect(() => {
    // Only reset if we're on the base /create page (not /create/[id])
    // and we have a session ID (indicating a workflow was stopped)
    const isBaseCreatePage = !window.location.pathname.includes('/create/') ||
      window.location.pathname === '/create';

    if (isBaseCreatePage && workflowState.sessionId) {
      logger.debug('Clearing workflow state due to session presence on /create', { component: 'CreatePage' });
      resetWorkflow();
    }
  }, [workflowState.sessionId, resetWorkflow]);

  // Redirect to dynamic route when session_id is available after starting new workflow
  useEffect(() => {
    if (workflowState.sessionId && workflowState.isLoading) {
      router.push(`/create/${workflowState.sessionId}`);
    }
  }, [workflowState.sessionId, workflowState.isLoading, router]);

  const handleMoodSubmit = async (mood: string, genreHint?: string) => {
    // Check if user is authenticated before starting workflow
    if (!isAuthenticated) {
      setShowLoginDialog(true);
      return;
    }

    try {
      await startWorkflow(mood, genreHint);
      // Note: Redirect happens in useEffect above when sessionId is set
    } catch (error) {
      logger.error('Failed to start workflow', error, { component: 'CreatePage' });
      // Show error toast
      const errorMessage = error instanceof Error ? error.message : 'Failed to start workflow';
      toast.error(errorMessage);
    }
  };

  const handleEditComplete = () => {
    // Navigate to playlist view to show final results
    if (workflowState.sessionId) {
      router.push(`/playlist/${workflowState.sessionId}`);
    }
  };

  const handleEditCancel = () => {
    // Go back to results view
    if (workflowState.sessionId) {
      router.push(`/playlist/${workflowState.sessionId}`);
    }
  };

  return {
    // State
    selectedMood,
    showLoginDialog,
    setShowLoginDialog,
    workflowState,

    // Handlers
    handleMoodSubmit,
    handleEditComplete,
    handleEditCancel,
  };
}

