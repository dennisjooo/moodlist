import { WorkflowProgressSkeleton } from './WorkflowProgressSkeleton';
import { BackButton } from '@/components/shared';
import { CreateSessionLayout, createSessionCardClassName } from '@/components/features/create/session/CreateSessionLayout';

interface CreateSessionSkeletonProps {
    onBack: () => void;
}

export function CreateSessionSkeleton({ onBack }: CreateSessionSkeletonProps) {
    return (
        <CreateSessionLayout>
            <BackButton
                onClick={onBack}
                animated
                className="w-fit"
            />

            <div className={`${createSessionCardClassName} space-y-6`}>
                <WorkflowProgressSkeleton />
            </div>
        </CreateSessionLayout>
    );
}
