import Navigation from '@/components/Navigation';
import MoodBackground from '@/components/shared/MoodBackground';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import WorkflowProgress from '@/components/WorkflowProgress';
import type { Track } from '@/lib/types/workflow';
import { cn } from '@/lib/utils';
import { ArrowLeft, Sparkles } from 'lucide-react';

interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface MoodAnalysis {
    color_scheme: ColorScheme;
    [key: string]: unknown;
}

interface CreateSessionProgressProps {
    sessionId: string;
    status: string | null;
    moodAnalysis?: MoodAnalysis;
    recommendations: Track[];
    colorScheme?: ColorScheme;
    isCancelling: boolean;
    onBack: () => void;
}

export function CreateSessionProgress({
    sessionId,
    status,
    colorScheme,
    isCancelling,
    onBack,
}: CreateSessionProgressProps) {
    const isTerminalStatus = status === 'completed' || status === 'failed';

    return (
        <>
            <div className={cn("min-h-screen bg-background relative flex flex-col", isCancelling && "opacity-60 pointer-events-none")}>
                <MoodBackground
                    colorScheme={colorScheme}
                    style="linear-diagonal"
                    opacity={0.2}
                />

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
                            onClick={onBack}
                            disabled={isCancelling}
                            className="mb-8 gap-2"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            {isCancelling ? 'Cancelling...' : 'Back'}
                        </Button>
                    </div>

                    {/* Centered content area */}
                    <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 -mt-16">
                        <div className="max-w-4xl w-full">
                            {/* Only show "Creating your playlist" if we have a status AND it's not terminal */}
                            {status && !isTerminalStatus && (
                                <div className="text-center mb-12">
                                    <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                                        <Sparkles className="w-4 h-4" />
                                        AI-Powered Playlist Creation
                                    </Badge>

                                    <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                                        {isCancelling ? 'Cancelling workflow...' : 'Creating your playlist'}
                                    </h1>
                                    <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                                        {isCancelling
                                            ? 'Please wait while we cancel your request.'
                                            : 'Our AI is working on creating the perfect Spotify playlist for your mood.'
                                        }
                                    </p>
                                </div>
                            )}

                            {/* Workflow Progress */}
                            {sessionId && status !== 'completed' && (
                                <div className="mb-8">
                                    <WorkflowProgress />
                                </div>
                            )}
                        </div>
                    </div>
                </main>
            </div>
        </>
    );
}
