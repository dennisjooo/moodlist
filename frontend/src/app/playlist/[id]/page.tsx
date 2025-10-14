'use client';

import Navigation from '@/components/Navigation';
import PlaylistResults from '@/components/PlaylistResults';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { LoadingDots } from '@/components/ui/loading-dots';
import { useAuth } from '@/lib/authContext';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { ArrowLeft } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';

function PlaylistPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const [isLoadingSession, setIsLoadingSession] = useState(true);
    const { workflowState, loadWorkflow } = useWorkflow();
    const { isAuthenticated, isLoading: authLoading } = useAuth();

    const handleBack = () => {
        router.push('/playlists');
    };

    const loadSessionCallback = useCallback(async () => {
        if (!sessionId) {
            router.push('/playlists');
            return;
        }

        // Wait for auth to finish loading
        if (authLoading) {
            return;
        }

        // Check authentication
        if (!isAuthenticated) {
            router.push('/');
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
    }, [sessionId, authLoading, isAuthenticated, workflowState.sessionId, workflowState.status, workflowState.isLoading, router, loadWorkflow]);

    // Load session if not already in context
    useEffect(() => {
        loadSessionCallback();
    }, [loadSessionCallback]);

    // Monitor workflow state to know when loading is complete
    useEffect(() => {
        if (workflowState.sessionId === sessionId && workflowState.status === 'completed') {
            setIsLoadingSession(false);
        }
        // If there's an error in workflow state, also stop loading
        else if (workflowState.error) {
            setIsLoadingSession(false);
        }
    }, [workflowState.sessionId, workflowState.status, workflowState.error, sessionId]);

    // Loading state - show while checking auth or loading playlist
    if (authLoading || isLoadingSession) {
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
                        <LoadingDots size="sm" />
                    </div>
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

                <PlaylistResults />
            </main>
        </div>
    );
}

export default function PlaylistPage() {
    return <PlaylistPageContent />;
}

