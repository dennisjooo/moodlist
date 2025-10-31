'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { logger } from '@/lib/utils/logger';
import { workflowEvents } from './useActiveWorkflows';

/**
 * Custom hook for managing workflow session loading and state
 * 
 * Handles:
 * - Loading workflow session from URL params
 * - Tracking loading state
 * - Redirecting on completion
 * - Error handling
 * 
 * @returns {Object} Session state and handlers
 */
export function useWorkflowSession() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const { workflowState, loadWorkflow } = useWorkflow();

  const loadSessionCallback = useCallback(async () => {
    logger.debug('[useWorkflowSession] loadSessionCallback called', {
      component: 'useWorkflowSession',
      sessionId,
      state: {
        sessionId: workflowState.sessionId,
        status: workflowState.status,
        isLoading: workflowState.isLoading,
      },
    });

    if (!sessionId) {
      router.push('/create');
      return;
    }

    // If we already have this session loaded with status, mark as done
    if (workflowState.sessionId === sessionId && workflowState.status !== null) {
      logger.debug('[useWorkflowSession] Session already loaded with status, skipping', {
        component: 'useWorkflowSession',
        sessionId
      });
      setIsLoadingSession(false);
      return;
    }

    // If workflow is already loading, don't start another load
    if (workflowState.isLoading) {
      logger.debug('[useWorkflowSession] Workflow already loading, waiting...', {
        component: 'useWorkflowSession',
        sessionId
      });
      return;
    }

    logger.info('[useWorkflowSession] Calling loadWorkflow', {
      component: 'useWorkflowSession',
      sessionId
    });

    await loadWorkflow(sessionId);
  }, [sessionId, workflowState.sessionId, workflowState.status, workflowState.isLoading, router, loadWorkflow]);

  // Load session if not already in context
  useEffect(() => {
    loadSessionCallback();
  }, [loadSessionCallback]);

  // Monitor workflow state to know when loading is complete
  useEffect(() => {
    if (workflowState.sessionId === sessionId && workflowState.status !== null) {
      setIsLoadingSession(false);
    } else if (workflowState.error) {
      setIsLoadingSession(false);
    }
  }, [workflowState.sessionId, workflowState.status, workflowState.error, sessionId]);

  // Redirect to playlist page if workflow is completed
  useEffect(() => {
    if (workflowState.status === 'completed' && workflowState.recommendations.length > 0 && workflowState.sessionId) {
      // Clear the notification indicator before redirecting
      logger.info('Removing completed workflow from active tracking before redirect', {
        component: 'useWorkflowSession',
        sessionId: workflowState.sessionId
      });
      workflowEvents.removed(workflowState.sessionId);

      router.push(`/playlist/${workflowState.sessionId}`);
    }
  }, [workflowState.status, workflowState.recommendations.length, workflowState.sessionId, router]);

  return {
    sessionId,
    isLoadingSession,
    workflowState,
    isTerminalStatus: workflowState.status === 'completed' || workflowState.status === 'failed',
  };
}

