'use client';

import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import PlaylistResults from '@/components/PlaylistResults';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import WorkflowProgress from '@/components/WorkflowProgress';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';

// Main content component for dynamic session route
function CreateSessionPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const [isMobile, setIsMobile] = useState(false);
    const [isLoadingSession, setIsLoadingSession] = useState(true);
    const { workflowState, startWorkflow, loadWorkflow } = useWorkflow();

    const handleBack = () => {
        // Check if there's history to go back to
        if (window.history.length > 2) {
            router.back();
        } else {
            // Default to playlists page if no history
            router.push('/playlists');
        }
    };

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    const loadSessionCallback = useCallback(async () => {
        console.log('[Page] loadSessionCallback called, sessionId:', sessionId, 'state:', {
            sessionId: workflowState.sessionId,
            status: workflowState.status,
            isLoading: workflowState.isLoading,
        });

        if (!sessionId) {
            router.push('/create');
            return;
        }

        // If we already have this session loaded with status, mark as done
        if (workflowState.sessionId === sessionId && workflowState.status !== null) {
            console.log('[Page] Session already loaded with status, skipping');
            setIsLoadingSession(false);
            return;
        }

        // If workflow is already loading, don't start another load
        if (workflowState.isLoading) {
            console.log('[Page] Workflow already loading, waiting...');
            return;
        }

        console.log('[Page] Calling loadWorkflow from page component');
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

    const handleEditComplete = () => {
        // Refresh the page to show final results
        window.location.reload();
    };

    const handleEditCancel = () => {
        // Go back to results view
        window.location.reload();
    };


    // Loading state - only show minimal loading indicator during initial auth/status check
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
                    {/* Back Button */}
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="mb-6 gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>

                    <div className="flex items-center justify-center min-h-[60vh]">
                        <div className="flex items-center justify-center space-x-2">
                            <div className="w-4 h-4 bg-primary rounded-full animate-bounce"></div>
                            <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    // Show editor if workflow is awaiting user input
    if (workflowState.awaitingInput && workflowState.recommendations.length > 0 && workflowState.sessionId) {
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
                    {/* Back Button */}
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="mb-6 gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>

                    <PlaylistEditor
                        sessionId={workflowState.sessionId}
                        recommendations={workflowState.recommendations}
                        onSave={handleEditComplete}
                        onCancel={handleEditCancel}
                    />
                </main>
            </div>
        );
    }

    // Determine if workflow is in a terminal state
    const isTerminalStatus = workflowState.status === 'completed' || workflowState.status === 'failed';

    // Show results if workflow is completed
    if (workflowState.status === 'completed' && workflowState.recommendations.length > 0) {
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
                    {/* Back Button */}
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

    // If workflow is in terminal state but no recommendations, show error or loading state
    if (isTerminalStatus && workflowState.recommendations.length === 0) {
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
                    {/* Back Button */}
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
                            {workflowState.error ? (
                                <div className="text-destructive">
                                    <p className="text-lg font-semibold mb-2">Error</p>
                                    <p className="text-muted-foreground">{workflowState.error}</p>
                                </div>
                            ) : (
                                <div className="flex items-center justify-center space-x-2">
                                    <div className="w-4 h-4 bg-primary rounded-full animate-bounce"></div>
                                    <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                    <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                </div>
                            )}
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background relative">
            {/* Fixed Dot Pattern Background */}
            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            {/* Navigation */}
            <Navigation />

            {/* Main Content */}
            <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                {/* Back Button */}
                <Button
                    variant="ghost"
                    onClick={handleBack}
                    className="mb-6 gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </Button>

                {/* Only show "Creating your playlist" if we have a status AND it's not terminal */}
                {workflowState.status && !isTerminalStatus && (
                    <div className="text-center mb-12">
                        <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                            <Sparkles className="w-4 h-4" />
                            AI-Powered Playlist Creation
                        </Badge>

                        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                            Creating your playlist
                        </h1>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            Our AI is working on creating the perfect Spotify playlist for your mood.
                        </p>
                    </div>
                )}

                {/* Workflow Progress */}
                {workflowState.sessionId && workflowState.status !== 'completed' && (
                    <div className="mb-8">
                        <WorkflowProgress />
                    </div>
                )}
            </main>
        </div>
    );
}

export default function CreateSessionPage() {
    return <CreateSessionPageContent />;
}

