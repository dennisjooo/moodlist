'use client';

import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { LoadingDots } from '@/components/ui/loading-dots';
import WorkflowProgress from '@/components/WorkflowProgress';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import { logger } from '@/lib/utils/logger';

// Main content component for dynamic session route
function CreateSessionPageContent() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.id as string;
    const [isMobile, setIsMobile] = useState(false);
    const [isLoadingSession, setIsLoadingSession] = useState(true);
    const { workflowState, startWorkflow, loadWorkflow } = useWorkflow();

    const handleBack = () => {
        // Check if we're currently on an edit page - if so, go back to the parent create page
        if (window.location.pathname.includes('/edit')) {
            const parentPath = window.location.pathname.replace('/edit', '');
            router.push(parentPath);
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

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

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
                        <LoadingDots size="sm" />
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
                                <LoadingDots size="sm" />
                            )}
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background relative flex flex-col">
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

            {/* Main Content - Centered */}
            <main className="relative z-10 flex-1 flex flex-col">
                <div className="max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* Back Button - Positioned at top */}
                    <Button
                        variant="ghost"
                        onClick={handleBack}
                        className="mb-8 gap-2"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </Button>
                </div>

                {/* Centered content area */}
                <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 -mt-16">
                    <div className="max-w-4xl w-full">
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
                    </div>
                </div>
            </main>
        </div>
    );
}

export default function CreateSessionPage() {
    return <CreateSessionPageContent />;
}

