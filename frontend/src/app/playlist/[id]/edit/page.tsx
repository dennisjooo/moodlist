'use client';

import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { LoadingDots } from '@/components/ui/loading-dots';
import { useAuth } from '@/lib/authContext';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { ArrowLeft } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthGuard } from '@/components/auth/AuthGuard';

function EditPlaylistPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const { workflowState, loadWorkflow } = useWorkflow();
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            // Wait for auth to complete
            if (authLoading) {
                return;
            }

            // Check authentication
            if (!isAuthenticated) {
                router.push('/');
                return;
            }

            if (sessionId) {
                await loadWorkflow(sessionId);
            }
            setIsLoading(false);
        };

        loadData();
    }, [sessionId, loadWorkflow, authLoading, isAuthenticated, router]);

    const handleDone = () => {
        router.push(`/playlist/${sessionId}`);
    };

    const handleCancel = () => {
        router.push(`/playlist/${sessionId}`);
    };

    // Loading state
    if (authLoading || isLoading || workflowState.isLoading) {
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

                <main className="relative z-10 flex items-center justify-center min-h-[calc(100vh-80px)]">
                    <div className="text-center">
                        <LoadingDots size="sm" />
                        <p className="mt-4 text-muted-foreground">Loading playlist...</p>
                    </div>
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
                            This playlist doesn't have any tracks yet.
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
        <AuthGuard allowOptimistic>
            <EditPlaylistPageContent />
        </AuthGuard>
    );
}

