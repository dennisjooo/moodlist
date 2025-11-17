'use client';

import { getWorkflowStatusMessage } from '@/lib/constants/workflowStatusMessages';

interface StatusMessageProps {
    status: string | null;
    currentStep?: string | null;
}

export function StatusMessage({ status, currentStep }: StatusMessageProps) {
    // Prioritize currentStep if available (it's more specific)
    const statusToCheck = currentStep || status;

    return (
        <div className="text-sm font-medium flex-1">
            {getWorkflowStatusMessage(statusToCheck)}
        </div>
    );
}

