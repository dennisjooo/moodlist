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
import { useEffect, useState } from 'react';

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

    // Load session if not already in context
    useEffect(() => {
        const loadSession = async () => {
            if (!sessionId) {
                router.push('/create');
                return;
            }

            // If we already have this session loaded, skip
            if (workflowState.sessionId === sessionId) {
                setIsLoadingSession(false);
                return;
            }

            try {
                // Load the workflow state from the API
                await loadWorkflow(sessionId);
                setIsLoadingSession(false);
            } catch (error) {
                console.error('Failed to load session:', error);
                // Session not found, redirect to create
                router.push('/create');
            }
        };

        loadSession();
    }, [sessionId, workflowState.sessionId, router, loadWorkflow]);

    const handleMoodSubmit = async (mood: string, genreHint?: string) => {
        try {
            await startWorkflow(mood, genreHint);
        } catch (error) {
            console.error('Failed to start workflow:', error);
        }
    };

    const handleEditComplete = () => {
        // Refresh the page to show final results
        window.location.reload();
    };

    const handleEditCancel = () => {
        // Go back to results view
        window.location.reload();
    };

    const mobileMoods = [
        'Chill Evening',
        'Energetic Workout',
        'Study Focus',
        'Road Trip',
        'Romantic Night',
        'Morning Coffee',
    ];

    const desktopMoods = [
        'Chill Evening',
        'Energetic Workout',
        'Study Focus',
        'Road Trip',
        'Romantic Night',
        'Morning Coffee',
        'Rainy Day',
        'Party Vibes',
        'Happy Sunshine',
        'Melancholy Blues',
        'Adventure Time',
        'Cozy Winter',
    ];

    const moods = isMobile ? mobileMoods : desktopMoods;

    // Loading state
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

                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="flex items-center space-x-2">
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

