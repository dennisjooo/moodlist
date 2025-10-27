import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { logger } from '@/lib/utils/logger';
import { sseManager } from '@/lib/sseManager';
import { pollingManager } from '@/lib/pollingManager';

interface UseWorkflowCancellationProps {
    sessionId: string | null;
    stopWorkflow: () => void;
    clearError: () => void;
}

export function useWorkflowCancellation({
    sessionId,
    stopWorkflow,
    clearError
}: UseWorkflowCancellationProps) {
    const router = useRouter();
    const [showCancelDialog, setShowCancelDialog] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);

    const handleCancelClick = () => {
        setShowCancelDialog(true);
    };

    const handleConfirmCancel = async () => {
        setShowCancelDialog(false);
        setIsCancelling(true);

        try {
            // Cancel the workflow on the backend if we have a session ID
            if (sessionId) {
                try {
                    const { workflowAPI } = await import('@/lib/workflowApi');
                    await workflowAPI.cancelWorkflow(sessionId);
                    logger.info('Workflow cancelled on backend', { component: 'useWorkflowCancellation', sessionId });
                } catch (error) {
                    logger.error('Failed to cancel workflow on backend', error, { component: 'useWorkflowCancellation', sessionId });
                    // Continue with local cleanup even if backend call fails
                }

                // Stop SSE/polling connections immediately to prevent further API calls
                logger.debug('Stopping SSE/polling connections for cancelled workflow', { component: 'useWorkflowCancellation', sessionId });
                sseManager.stopStreaming(sessionId);
                pollingManager.stopPolling(sessionId);
            }

            // Clean up local state
            stopWorkflow();

            // Clear any errors that might be showing
            clearError();

            // Navigate to /create and force a clean state by using replace
            // This ensures we go back to the initial state with the mood input form
            router.replace('/create');
        } finally {
            // Reset cancelling state (though we'll likely navigate away before this)
            setIsCancelling(false);
        }
    };

    return {
        showCancelDialog,
        setShowCancelDialog,
        isCancelling,
        handleCancelClick,
        handleConfirmCancel,
    };
}
