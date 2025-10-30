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
    const colorScheme = workflowState.moodAnalysis?.color_scheme;

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

    const cardClassName = cn(
        'rounded-3xl border border-border/50 bg-background/75 p-6 sm:p-8',
        'shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl'
    );

    let content;

    if (isLoadingSession) {
        content = (
            <div className={cn(cardClassName, 'space-y-6')}>
                <div className="space-y-2">
                    <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                        Preparing your playlist
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        We&apos;re syncing the latest details from your session. Hang tight for your curated mix.
                    </p>
                </div>
                <PlaylistResultsSkeleton />
            </div>
        );
    } else if (workflowState.error || workflowState.status !== 'completed') {
        content = (
            <div className={cn(cardClassName, 'space-y-6 text-center')}>
                <div className="space-y-2">
                    <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                        Playlist not available
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {workflowState.error || 'This playlist is not available yet or may have been removed.'}
                    </p>
                </div>
                <div className="flex justify-center">
                    <Button onClick={() => router.push('/create')} className="gap-2">
                        Create a new playlist
                    </Button>
                </div>
            </div>
        );
    } else {
        content = (
            <div className={cardClassName}>
                <PlaylistResults />
            </div>
        );
    }

    return (
        <div
            className={cn(
                'relative h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-background',
                'flex flex-col'
            )}
        >
            <MoodBackground colorScheme={colorScheme} style="linear-diagonal" opacity={0.18} />

            <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        '[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]',
                    )}
                />
            </div>

            <Navigation />

            <main className="relative z-10 mx-auto flex w-full max-w-5xl flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-8">
                <div className="flex w-full flex-col gap-6">
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="w-fit gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>

                    {content}
                </div>
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

