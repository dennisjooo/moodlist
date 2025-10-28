'use client';

import { Badge } from '@/components/ui/badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useRouter, usePathname } from 'next/navigation';
import { Loader2, ChevronDown } from 'lucide-react';
import { useActiveWorkflows } from '@/lib/hooks/useActiveWorkflows';
import { useGlobalWorkflowPolling } from '@/lib/hooks/useGlobalWorkflowPolling';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';

export function WorkflowNotificationIndicator() {
    const router = useRouter();
    const pathname = usePathname();
    const { activeWorkflows, hasActiveWorkflows } = useActiveWorkflows();
    const { workflowState } = useWorkflow();

    // Determine if we're on a /create/[id] page with active workflow
    // If so, exclude that session from global polling since WorkflowContext is already polling it
    const isOnCreatePage = pathname?.startsWith('/create/') && pathname.split('/').length === 3;
    const excludeSessionId = isOnCreatePage ? workflowState.sessionId : null;

    // Enable global polling for all active workflows except the one being polled by WorkflowContext
    useGlobalWorkflowPolling(activeWorkflows.map(w => w.sessionId), excludeSessionId);

    if (!hasActiveWorkflows) {
        return null;
    }

    const totalActive = activeWorkflows.length;
    const displayText = totalActive === 1
        ? 'Creating...'
        : `${totalActive} creating...`;

    const handleWorkflowClick = (sessionId: string) => {
        router.push(`/create/${sessionId}`);
    };

    const formatMoodPrompt = (prompt: string) => {
        // Truncate long prompts
        return prompt.length > 40 ? `${prompt.slice(0, 40)}...` : prompt;
    };

    const getStatusDisplay = (status: string) => {
        // Make status more readable
        return status
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button
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
                    <ChevronDown className="w-3 h-3 text-primary" />
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[280px]">
                <DropdownMenuLabel>Active Workflows</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {activeWorkflows.map((workflow, index) => (
                    <DropdownMenuItem
                        key={workflow.sessionId}
                        onClick={() => handleWorkflowClick(workflow.sessionId)}
                        className="flex flex-col items-start gap-1 py-2 cursor-pointer"
                    >
                        <div className="flex items-center gap-2 w-full">
                            <Loader2 className="w-3 h-3 text-primary animate-spin flex-shrink-0" />
                            <span className="text-sm font-medium truncate flex-1">
                                {formatMoodPrompt(workflow.moodPrompt)}
                            </span>
                        </div>
                        <span className="text-xs text-muted-foreground pl-5">
                            {getStatusDisplay(workflow.status)}
                        </span>
                    </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

