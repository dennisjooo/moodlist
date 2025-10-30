import { WorkflowProgressSkeleton } from '@/components/shared/LoadingStates';
import { Button } from '@/components/ui/button';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import { ArrowLeft } from 'lucide-react';

interface ColorScheme {
    primary: string;
    secondary: string;
    tertiary: string;
}

interface CreateSessionErrorProps {
    colorScheme?: ColorScheme;
    error?: string | null;
    onBack: () => void;
}

export function CreateSessionError({
    colorScheme,
    error,
    onBack,
}: CreateSessionErrorProps) {
    return (
        <CreateSessionLayout colorScheme={colorScheme}>
            <Button
                variant="ghost"
                onClick={onBack}
                className="w-fit gap-2"
            >
                <ArrowLeft className="w-4 h-4" />
                Back
            </Button>

            <div className={`${createSessionCardClassName} flex min-h-[280px] items-center justify-center text-center`}>
                {error ? (
                    <div className="space-y-2">
                        <p className="text-lg font-semibold text-destructive">Something went wrong</p>
                        <p className="text-sm text-muted-foreground">{error}</p>
                    </div>
                ) : (
                    <div className="w-full max-w-3xl">
                        <WorkflowProgressSkeleton />
                    </div>
                )}
            </div>
        </CreateSessionLayout>
    );
}
