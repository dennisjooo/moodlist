import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import WorkflowProgress from '@/components/WorkflowProgress';
import { ArrowLeft, Sparkles } from 'lucide-react';

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
    const isTerminalStatus = status === 'completed' || status === 'failed' || status === 'cancelled';

    return (
        <CreateSessionLayout colorScheme={colorScheme} dimmed={isCancelling}>
            <Button
                variant="ghost"
                onClick={onBack}
                disabled={isCancelling}
                className="w-fit gap-2"
            >
                <ArrowLeft className="w-4 h-4" />
                {isCancelling ? 'Cancelling...' : 'Back'}
            </Button>

            <div className={`${createSessionCardClassName} space-y-10`}>
                {status && !isTerminalStatus && (
                    <div className="space-y-4 text-center">
                        <Badge
                            variant="outline"
                            className="mx-auto flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-4 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur"
                        >
                            <Sparkles className="h-4 w-4" />
                            AI-Powered Playlist Creation
                        </Badge>

                        <div className="space-y-2">
                            <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                                {isCancelling ? 'Cancelling workflow...' : 'Crafting your playlist'}
                            </h1>
                            <p className="mx-auto max-w-2xl text-sm text-muted-foreground sm:text-base">
                                {isCancelling
                                    ? 'Please wait while we cancel your request.'
                                    : 'We are weaving together tracks that match the feeling you shared. Hang tight while the mix comes to life.'}
                            </p>
                        </div>
                    </div>
                )}

                {sessionId && status !== 'completed' && (
                    <div className="space-y-4">
                        <WorkflowProgress />
                    </div>
                )}
            </div>
        </CreateSessionLayout>
    );
}
