import { WorkflowProgressSkeleton } from '@/components/shared/LoadingStates';
import { Button } from '@/components/ui/button';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/CreateSessionLayout';
import { ArrowLeft } from 'lucide-react';

interface CreateSessionSkeletonProps {
    onBack: () => void;
}

export function CreateSessionSkeleton({ onBack }: CreateSessionSkeletonProps) {
    return (
        <CreateSessionLayout>
            <Button
                variant="ghost"
                onClick={onBack}
                className="w-fit gap-2"
            >
                <ArrowLeft className="w-4 h-4" />
                Back
            </Button>

            <div className={`${createSessionCardClassName} flex min-h-[320px] items-center justify-center`}>
                <div className="w-full max-w-3xl">
                    <WorkflowProgressSkeleton />
                </div>
            </div>
        </CreateSessionLayout>
    );
}
