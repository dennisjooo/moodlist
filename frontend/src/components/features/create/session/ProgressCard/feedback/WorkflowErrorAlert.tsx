'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface WorkflowErrorAlertProps {
    message: string | null;
    onRetry: () => void;
}

export function WorkflowErrorAlert({ message, onRetry }: WorkflowErrorAlertProps) {
    if (!message) return null;

    return (
        <Alert variant="destructive" className="border-destructive/50 bg-destructive/5">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between gap-3">
                <span className="flex-1 text-sm">{message}</span>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onRetry}
                    className="shrink-0 border-destructive/30 hover:bg-destructive hover:text-destructive-foreground"
                >
                    Retry
                </Button>
            </AlertDescription>
        </Alert>
    );
}
