'use client';

import { Badge } from '@/components/ui/badge';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useActiveWorkflows } from '@/lib/hooks/useActiveWorkflows';

export function WorkflowNotificationIndicator() {
    const router = useRouter();
    const { activeWorkflows, hasActiveWorkflows } = useActiveWorkflows();

    if (!hasActiveWorkflows) {
        return null;
    }

    const handleClick = () => {
        // Navigate to the most recent active workflow
        const mostRecent = activeWorkflows[0];
        if (mostRecent) {
            router.push(`/create/${mostRecent.sessionId}`);
        }
    };

    const totalActive = activeWorkflows.length;
    const displayText = totalActive === 1
        ? 'Creating...'
        : `${totalActive} creating...`;

    return (
        <button
            onClick={handleClick}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary/10 hover:bg-primary/20 transition-colors"
            aria-label="Active workflow notifications"
        >
            <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
            <span className="text-xs font-medium text-primary hidden sm:inline">
                {displayText}
            </span>
            {totalActive > 1 && (
                <Badge variant="secondary" className="h-5 min-w-5 flex items-center justify-center text-xs px-1.5">
                    {totalActive}
                </Badge>
            )}
        </button>
    );
}

