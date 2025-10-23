'use client';

import { AuthGuard } from '@/components/AuthGuard';
import Navigation from '@/components/Navigation';
import { PlaylistEditorSkeleton } from '@/components/shared/LoadingStates';
import MoodBackground from '@/components/shared/MoodBackground';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { cn } from '@/lib/utils';
import { ArrowLeft } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
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

    useEffect(() => {
        const loadData = async () => {
            if (sessionId) {
                await loadWorkflow(sessionId);
            }
            setIsLoading(false);
        };

        loadData();
    }, [sessionId, loadWorkflow]);

    const handleDone = () => {
        router.push(`/playlist/${sessionId}`);
    };

    const handleCancel = () => {
        router.push(`/playlist/${sessionId}`);
    };

    // Loading state
    if (isLoading || workflowState.isLoading) {
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

                <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <PlaylistEditorSkeleton />
                </main>
            </div>
        );
    }

    // Error state
    if (workflowState.error || !workflowState.sessionId) {
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
    if (!workflowState.recommendations || workflowState.recommendations.length === 0) {
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

            <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                {/* Back Button */}
                <Button
                    variant="ghost"
                    onClick={handleCancel}
                    className="mb-6 gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Playlist
                </Button>

                <PlaylistEditor
                    sessionId={workflowState.sessionId}
                    recommendations={workflowState.recommendations}
                    isCompleted={hasSavedToSpotify}
                    onSave={handleDone}
                    onCancel={handleCancel}
                />
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

