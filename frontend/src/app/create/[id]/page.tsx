'use client';

import { AuthGuard } from '@/components/AuthGuard';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { logger } from '@/lib/utils/logger';
import { usePageCancellation } from '@/lib/hooks/usePageCancellation';
import { CreateSessionLoading } from '@/components/features/create/CreateSessionLoading';
import { CreateSessionEditor } from '@/components/features/create/CreateSessionEditor';
import { CreateSessionProgress } from '@/components/features/create/CreateSessionProgress';
import { CreateSessionError } from '@/components/features/create/CreateSessionError';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

// Main content component for dynamic session route
function CreateSessionPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const [isLoadingSession, setIsLoadingSession] = useState(true);
    const { workflowState, loadWorkflow, stopWorkflow, clearError } = useWorkflow();

    const {
        showCancelDialog,
        setShowCancelDialog,
        isCancelling,
        handleConfirmCancel,
    } = usePageCancellation({
        sessionId: workflowState.sessionId,
        stopWorkflow,
        clearError,
    });

    const handleBack = () => {
        // Check if we're currently on an edit page - if so, go back to the parent create page
        if (window.location.pathname.includes('/edit')) {
            const parentPath = window.location.pathname.replace('/edit', '');
            router.push(parentPath);
            return;
        }

        // If workflow is active (not terminal), show confirmation dialog
        const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';
        if (isActive && workflowState.sessionId) {
            setShowCancelDialog(true);
            return;
        }

        // Determine navigation origin and destination
        const referrer = document.referrer;
        const currentPath = window.location.pathname;

        // If user came from playlists page, go back there
        if (referrer.includes('/playlists')) {
            router.push('/playlists');
        }
        // If user came from /create page, go back there
        else if (referrer.includes('/create') && !referrer.includes('/create/')) {
            router.push('/create');
        }
        // If referrer is unclear but we have a session ID, user likely came from playlists
        else if (currentPath.includes('/create/') && sessionId) {
            router.push('/playlists');
        }
        // Default fallback to playlists
        else {
            router.push('/playlists');
        }
    };



    const loadSessionCallback = useCallback(async () => {
        logger.debug('[Page] loadSessionCallback called', {
            component: 'CreateSessionPage',
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
            logger.debug('[Page] Session already loaded with status, skipping', { component: 'CreateSessionPage', sessionId });
            setIsLoadingSession(false);
            return;
        }

        // If workflow is already loading, don't start another load
        if (workflowState.isLoading) {
            logger.debug('[Page] Workflow already loading, waiting...', { component: 'CreateSessionPage', sessionId });
            return;
        }

        logger.info('[Page] Calling loadWorkflow from page component', { component: 'CreateSessionPage', sessionId });
        // Load the workflow state from the API
        // The workflowContext will handle waiting for auth to complete
        await loadWorkflow(sessionId);

        // Don't immediately mark as done - wait for workflow state to be populated
        // The useEffect below will handle this
    }, [sessionId, workflowState.sessionId, workflowState.status, workflowState.isLoading, router, loadWorkflow]);

    // Load session if not already in context
    useEffect(() => {
        loadSessionCallback();
    }, [loadSessionCallback]);

    // Monitor workflow state to know when loading is complete
    useEffect(() => {
        // Only stop loading when we have both session ID AND status
        // This ensures content is ready to display before hiding loading dots
        if (workflowState.sessionId === sessionId && workflowState.status !== null) {
            setIsLoadingSession(false);
        }
        // If there's an error in workflow state, also stop loading
        else if (workflowState.error) {
            setIsLoadingSession(false);
        }
    }, [workflowState.sessionId, workflowState.status, workflowState.error, sessionId]);

    // Redirect to playlist page if workflow is completed
    useEffect(() => {
        if (workflowState.status === 'completed' && workflowState.recommendations.length > 0 && workflowState.sessionId) {
            router.push(`/playlist/${workflowState.sessionId}`);
        }
    }, [workflowState.status, workflowState.recommendations.length, workflowState.sessionId, router]);

    const handleEditComplete = () => {
        // Navigate to playlist view to show final results
        router.push(`/playlist/${sessionId}`);
    };

    const handleEditCancel = () => {
        // Go back to results view
        router.push(`/playlist/${sessionId}`);
    };

    // Determine which component to render based on workflow state
    const renderContent = () => {
        // Loading state - only show minimal loading indicator during initial auth/status check
        if (isLoadingSession) {
            return <CreateSessionLoading onBack={handleBack} />;
        }

        // Show editor if workflow is awaiting user input
        if (workflowState.awaitingInput && workflowState.recommendations.length > 0 && workflowState.sessionId) {
            const colorScheme = workflowState.moodAnalysis?.color_scheme;
            return (
                <CreateSessionEditor
                    sessionId={workflowState.sessionId}
                    recommendations={workflowState.recommendations}
                    colorScheme={colorScheme}
                    onBack={handleBack}
                    onSave={handleEditComplete}
                    onCancel={handleEditCancel}
                />
            );
        }

        // Determine if workflow is in a terminal state
        const isTerminalStatus = workflowState.status === 'completed' || workflowState.status === 'failed';

        // If workflow is in terminal state but no recommendations, show error or loading state
        if (isTerminalStatus && workflowState.recommendations.length === 0) {
            const colorScheme = workflowState.moodAnalysis?.color_scheme;
            return (
                <CreateSessionError
                    colorScheme={colorScheme}
                    error={workflowState.error}
                    onBack={handleBack}
                />
            );
        }

        // Default progress view
        const colorScheme = workflowState.moodAnalysis?.color_scheme;
        return (
            <CreateSessionProgress
                sessionId={workflowState.sessionId || ''}
                status={workflowState.status}
                moodAnalysis={workflowState.moodAnalysis}
                recommendations={workflowState.recommendations}
                colorScheme={colorScheme}
                isCancelling={isCancelling}
                onBack={handleBack}
            />
        );
    };

    return (
        <>
            {renderContent()}

            <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Cancel Playlist Creation?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to cancel this workflow? Your progress will be lost and you'll need to start over.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={isCancelling}>Keep Working</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmCancel}
                            disabled={isCancelling}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {isCancelling ? 'Cancelling...' : 'Cancel Workflow'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}

export default function CreateSessionPage() {
    return (
        <AuthGuard optimistic={true}>
            <CreateSessionPageContent />
        </AuthGuard>
    );
}

