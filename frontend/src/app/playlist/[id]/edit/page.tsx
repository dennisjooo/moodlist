'use client';

import { AuthGuard } from '@/components/AuthGuard';
import Navigation from '@/components/Navigation';
import { PlaylistEditorSkeleton } from '@/components/shared/LoadingStates';
import MoodBackground from '@/components/shared/MoodBackground';
import { BackButton } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const MIN_SKELETON_VISIBLE_MS = 300;
const SKELETON_FADE_OUT_MS = 450;
const PlaylistEditor = dynamic(() => import('@/components/PlaylistEditor'), {
    loading: () => <PlaylistEditorSkeleton />,
    ssr: false,
});

function EditPlaylistPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const { workflowState, loadWorkflow } = useWorkflow();
    const [isLoading, setIsLoading] = useState(true);
    const [showSkeleton, setShowSkeleton] = useState(true);
    const [renderSkeleton, setRenderSkeleton] = useState(true);
    const workflowIsLoading = isLoading || workflowState.isLoading;

    useEffect(() => {
        const loadData = async () => {
            if (sessionId) {
                await loadWorkflow(sessionId);
            }
            setIsLoading(false);
        };

        loadData();
    }, [sessionId, loadWorkflow]);

    // Provide a short overlap so the skeleton can fade out smoothly before the editor appears.
    useEffect(() => {
        let minTimer: ReturnType<typeof setTimeout> | undefined;

        if (!workflowIsLoading) {
            minTimer = setTimeout(() => {
                setShowSkeleton(false);
            }, MIN_SKELETON_VISIBLE_MS);
        } else {
            setShowSkeleton(true);
            setRenderSkeleton(true);
        }

        return () => {
            if (minTimer) {
                clearTimeout(minTimer);
            }
        };
    }, [workflowIsLoading]);

    useEffect(() => {
        let fadeTimer: ReturnType<typeof setTimeout> | undefined;

        if (!showSkeleton) {
            fadeTimer = setTimeout(() => {
                setRenderSkeleton(false);
            }, SKELETON_FADE_OUT_MS);
        } else {
            setRenderSkeleton(true);
        }

        return () => {
            if (fadeTimer) {
                clearTimeout(fadeTimer);
            }
        };
    }, [showSkeleton]);

    const handleDone = () => {
        router.push(`/playlist/${sessionId}`);
    };

    const handleCancel = () => {
        router.push(`/playlist/${sessionId}`);
    };

    // Error state
    if (!workflowIsLoading && (workflowState.error || !workflowState.sessionId)) {
        return (
            <div className="min-h-screen bg-background relative">
                <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_2.5s_cubic-bezier(0.22,0.61,0.36,1)_forwards]">
                    <DotPattern
                        className={cn(
                            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                        )}
                    />
                </div>
                <Navigation />
                <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <div className="text-center">
                        <h2 className="text-2xl font-bold mb-4">Playlist Not Found</h2>
                        <p className="text-muted-foreground mb-6">
                            {workflowState.error || 'Unable to load playlist'}
                        </p>
                        <Button onClick={() => router.push('/create')}>
                            Create New Playlist
                        </Button>
                    </div>
                </main>
            </div>
        );
    }

    // No recommendations
    if (
        !workflowIsLoading &&
        (!workflowState.recommendations || workflowState.recommendations.length === 0)
    ) {
        return (
            <div className="min-h-screen bg-background relative">
                <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_2.5s_cubic-bezier(0.22,0.61,0.36,1)_forwards]">
                    <DotPattern
                        className={cn(
                            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                        )}
                    />
                </div>
                <Navigation />
                <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <div className="text-center">
                        <h2 className="text-2xl font-bold mb-4">No Tracks Found</h2>
                        <p className="text-muted-foreground mb-6">
                            This playlist doesn&apos;t have any tracks yet.
                        </p>
                        <Button onClick={() => router.push(`/playlist/${sessionId}`)}>
                            Go Back
                        </Button>
                    </div>
                </main>
            </div>
        );
    }

    const hasSavedToSpotify = !!workflowState.playlist?.id;
    const colorScheme = workflowState.moodAnalysis?.color_scheme;
    const canRenderEditor =
        !workflowIsLoading &&
        workflowState.sessionId &&
        workflowState.recommendations &&
        workflowState.recommendations.length > 0;

    return (
        <div className="min-h-screen bg-background relative">
            <MoodBackground
                colorScheme={colorScheme}
                style="linear-diagonal"
                opacity={0.2}
            />

            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_2.5s_cubic-bezier(0.22,0.61,0.36,1)_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            <Navigation />

            <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="relative">
                    {renderSkeleton && (
                        <div
                            className={cn(
                                'transition-opacity duration-500 will-change-opacity',
                                showSkeleton
                                    ? 'opacity-100'
                                    : 'opacity-0 pointer-events-none absolute inset-0',
                            )}
                        >
                            <PlaylistEditorSkeleton />
                        </div>
                    )}

                    <div
                        className={cn(
                            'transition-all duration-700 ease-out transform',
                            !canRenderEditor && 'opacity-0 pointer-events-none',
                            canRenderEditor &&
                            (showSkeleton
                                ? 'opacity-0 translate-y-4 pointer-events-none'
                                : 'opacity-100 translate-y-0'),
                        )}
                    >
                        {canRenderEditor && (
                            <>
                                {/* Back Button */}
                                <BackButton
                                    onClick={handleCancel}
                                    animated
                                    className="mb-8"
                                >
                                    Back to Playlist
                                </BackButton>

                                <PlaylistEditor
                                    sessionId={workflowState.sessionId!}
                                    recommendations={workflowState.recommendations}
                                    isCompleted={hasSavedToSpotify}
                                    onSave={handleDone}
                                    onCancel={handleCancel}
                                />
                            </>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}

export default function EditPlaylistPage() {
    return (
        <AuthGuard optimistic={true}>
            <EditPlaylistPageContent />
        </AuthGuard>
    );
}
