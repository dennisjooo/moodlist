import { Badge } from '@/components/ui/badge';
import { BackButton } from '@/components/shared';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import WorkflowProgress from '@/components/WorkflowProgress';
import { Sparkles } from 'lucide-react';
import { isTerminalStatus } from '@/lib/utils/workflow';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { RealtimeTrackList } from './RealtimeTrackList';
interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface CreateSessionProgressProps {
    sessionId: string;
    status: string | null;
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
    const isTerminal = isTerminalStatus(status);
    const { workflowState } = useWorkflow();
    
    // Show tracks when we have some recommendations and we're in an active state
    const showTracks = workflowState.recommendations.length > 0 && !isTerminal;

    return (
        <CreateSessionLayout colorScheme={colorScheme} dimmed={isCancelling}>
            <BackButton
                onClick={onBack}
                disabled={isCancelling}
                animated
                className="w-fit"
            >
                {isCancelling ? 'Cancelling...' : 'Back'}
            </BackButton>

            <div className={`${createSessionCardClassName} space-y-6`}>
                {status && !isTerminal && (
                    <div className="space-y-3 text-center">
                        <Badge
                            variant="outline"
                            className="mx-auto flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-4 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur"
                        >
                            <Sparkles className="h-4 w-4" />
                            AI-Powered Playlist Creation
                        </Badge>

                        <div className="space-y-1">
                            <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                                {isCancelling ? 'Cancelling workflow...' : 'Crafting your playlist'}
                            </h1>
                            <p className="mx-auto max-w-2xl text-sm text-muted-foreground">
                                {isCancelling
                                    ? 'Please wait while we cancel your request.'
                                    : (
                                        <>
                                            We are weaving together tracks that match the feeling you shared.
                                            <br />
                                            {showTracks ? 'Watch as we build your perfect mix.' : 'Hang tight while the mix comes to life.'}
                                        </>
                                    )}
                            </p>
                        </div>
                    </div>
                )}

                {sessionId && status !== 'completed' && (
                    <div className="space-y-4">
                        <WorkflowProgress />
                        
                        {/* Show real-time track list when tracks start arriving */}
                        {showTracks && (
                            <div className="mt-8">
                                <RealtimeTrackList tracks={workflowState.recommendations} />
                            </div>
                        )}
                    </div>
                )}
            </div>
        </CreateSessionLayout>
    );
}
