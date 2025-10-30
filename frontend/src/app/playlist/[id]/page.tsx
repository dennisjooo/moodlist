'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { PlaylistResultsSkeleton } from '@/components/shared/LoadingStates';
import { Button } from '@/components/ui/button';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { workflowEvents } from '@/lib/hooks';
import { logger } from '@/lib/utils/logger';
import { ArrowLeft } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

const PlaylistResults = dynamic(() => import('@/components/PlaylistResults'), {
    loading: () => <PlaylistResultsSkeleton />,
});

function PlaylistPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const [isLoadingSession, setIsLoadingSession] = useState(true);
    const { workflowState, loadWorkflow, syncFromSpotify } = useWorkflow();
    const { isAuthenticated } = useAuth();
    const [hasAutoSynced, setHasAutoSynced] = useState(false);

    const handleBack = () => {
        router.push('/playlists');
    };

    const loadSessionCallback = useCallback(async () => {
        if (!sessionId) {
            router.push('/playlists');
            return;
        }

        // If we already have this session loaded with completed status, mark as done
        if (workflowState.sessionId === sessionId && workflowState.status === 'completed') {
            setIsLoadingSession(false);
            return;
        }

        // If workflow is already loading, don't start another load
        if (workflowState.isLoading) {
            return;
        }

        // Load the workflow state from the API
        await loadWorkflow(sessionId);
    }, [sessionId, workflowState.sessionId, workflowState.status, workflowState.isLoading, router, loadWorkflow]);

    // Load session if not already in context
    useEffect(() => {
        loadSessionCallback();
    }, [loadSessionCallback]);

    // Monitor workflow state to know when loading is complete
    useEffect(() => {
        if (workflowState.sessionId === sessionId && workflowState.status === 'completed') {
            setIsLoadingSession(false);

            // Remove this workflow from active workflows tracking since it's completed
            // and we're now viewing the final playlist
            logger.info('Removing completed workflow from active tracking', {
                component: 'PlaylistPage',
                sessionId
            });
            workflowEvents.removed(sessionId);
        }
        // If there's an error in workflow state, also stop loading
        else if (workflowState.error) {
            setIsLoadingSession(false);
        }
    }, [workflowState.sessionId, workflowState.status, workflowState.error, sessionId]);

    // Auto-sync from Spotify when playlist is loaded and has been saved to Spotify
    useEffect(() => {
        const shouldAutoSync =
            !hasAutoSynced &&
            !isLoadingSession &&
            isAuthenticated &&
            workflowState.sessionId === sessionId &&
            workflowState.status === 'completed' &&
            workflowState.playlist?.id; // Only sync if saved to Spotify

        if (shouldAutoSync) {
            setHasAutoSynced(true);
            syncFromSpotify().catch(error => {
                logger.error('Auto-sync failed', error, { component: 'PlaylistPage', sessionId });
            });
        }
    }, [
        hasAutoSynced,
        isLoadingSession,
        isAuthenticated,
        workflowState.sessionId,
        workflowState.status,
        workflowState.playlist?.id,
        sessionId,
        syncFromSpotify
    ]);

    const colorScheme = workflowState.moodAnalysis?.color_scheme;

    // Loading state - show while loading playlist
    if (isLoadingSession) {
        return (
            <CreateSessionLayout colorScheme={colorScheme}>
                <Button
                    variant="ghost"
                    onClick={handleBack}
                    className="w-fit gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </Button>

                <div className={cn(createSessionCardClassName, 'space-y-6 sm:space-y-8')}>
                    <PlaylistResultsSkeleton />
                </div>
            </CreateSessionLayout>
        );
    }

    // Error state
    if (workflowState.error || workflowState.status !== 'completed') {
        return (
            <CreateSessionLayout colorScheme={colorScheme}>
                <Button
                    variant="ghost"
                    onClick={handleBack}
                    className="w-fit gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </Button>

                <div
                    className={cn(
                        createSessionCardClassName,
                        'flex min-h-[320px] flex-col items-center justify-center space-y-4 text-center'
                    )}
                >
                    <div className="space-y-2">
                        <h2 className="text-2xl font-semibold tracking-tight">Playlist Not Found</h2>
                        <p className="text-sm text-muted-foreground">
                            {workflowState.error || 'This playlist is not available or still being created.'}
                        </p>
                    </div>
                    <Button onClick={() => router.push('/create')}>
                        Create New Playlist
                    </Button>
                </div>
            </CreateSessionLayout>
        );
    }

    // Show playlist results
    return (
        <CreateSessionLayout colorScheme={colorScheme}>
            <Button
                variant="ghost"
                onClick={handleBack}
                className="w-fit gap-2"
            >
                <ArrowLeft className="w-4 h-4" />
                Back
            </Button>

            <div className={cn(createSessionCardClassName, 'space-y-6 sm:space-y-8')}>
                <PlaylistResults />
            </div>
        </CreateSessionLayout>
    );
}

export default function PlaylistPage() {
    return (
        <AuthGuard optimistic={true}>
            <PlaylistPageContent />
        </AuthGuard>
    );
}

