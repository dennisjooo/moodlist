'use client';

import { AuthGuard } from '@/components/AuthGuard';
import Navigation from '@/components/Navigation';
import { PlaylistResultsSkeleton } from '@/components/shared/LoadingStates';
import MoodBackground from '@/components/shared/MoodBackground';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { workflowEvents } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { ArrowLeft } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
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

    // Loading state - show while loading playlist
    if (isLoadingSession) {
        return (
            <div className="min-h-screen bg-background relative">
                <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                    <DotPattern
                        className={cn(
                            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                        )}
                    />
                </div>

                <Navigation />

                <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="mb-6 gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>

                    <PlaylistResultsSkeleton />
                </main>
            </div>
        );
    }

    // Error state
    if (workflowState.error || workflowState.status !== 'completed') {
        return (
            <div className="min-h-screen bg-background relative">
                <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                    <DotPattern
                        className={cn(
                            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                        )}
                    />
                </div>

                <Navigation />

                <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="mb-6 gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>

                    <div className="flex items-center justify-center min-h-[60vh]">
                        <div className="text-center">
                            <h2 className="text-2xl font-bold mb-4">Playlist Not Found</h2>
                            <p className="text-muted-foreground mb-6">
                                {workflowState.error || 'This playlist is not available or still being created.'}
                            </p>
                            <Button onClick={() => router.push('/create')}>
                                Create New Playlist
                            </Button>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    // Show playlist results
    const colorScheme = workflowState.moodAnalysis?.color_scheme;

    return (
        <div className="min-h-screen bg-background relative">
            <MoodBackground
                colorScheme={colorScheme}
                style="linear-diagonal"
                opacity={0.2}
            />

            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            <Navigation />

            <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                <Button
                    variant="ghost"
                    onClick={handleBack}
                    className="mb-6 gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </Button>

                <PlaylistResults />
            </main>
        </div>
    );
}

export default function PlaylistPage() {
    return (
        <AuthGuard optimistic={true}>
            <PlaylistPageContent />
        </AuthGuard>
    );
}

