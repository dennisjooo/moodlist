'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { AlertCircle } from 'lucide-react';
import { MoodAnalysisDisplay } from './MoodAnalysisDisplay';
import { ProgressTimeline } from './ProgressTimeline';
import { StatusIcon } from './StatusIcon';
import { StatusMessage } from './StatusMessage';
import { WorkflowInsights } from './WorkflowInsights';
import { CancelWorkflowDialog } from './CancelWorkflowDialog';
import { useWorkflowCancellation } from '@/lib/hooks';
import { useEffect } from 'react';

export function WorkflowProgress() {
    const { workflowState, stopWorkflow, clearError } = useWorkflow();
    const {
        showCancelDialog,
        setShowCancelDialog,
        isCancelling,
        handleCancelClick,
        handleConfirmCancel,
    } = useWorkflowCancellation({
        sessionId: workflowState.sessionId,
        stopWorkflow,
        clearError,
    });

    // Debug: Log when workflowState changes
    useEffect(() => {
        logger.debug('WorkflowProgress render', {
            status: workflowState.status,
            step: workflowState.currentStep,
        });
    }, [workflowState.status, workflowState.currentStep]);

    const handleRetry = () => {
        clearError();
        // The workflow will automatically restart polling
    };

    if (!workflowState.sessionId && !workflowState.isLoading) {
        return null;
    }

    const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';

    return (
        <>
            <Card className={cn("w-full overflow-hidden", isCancelling && "opacity-60 pointer-events-none")}>
                <CardHeader className="pb-3 overflow-hidden">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <StatusIcon status={workflowState.status} />
                            {isCancelling ? 'Cancelling...' : 'Playlist Generation'}
                        </CardTitle>
                        {workflowState.sessionId && isActive && !isCancelling && (
                            <Button variant="outline" size="sm" onClick={handleCancelClick}>
                                Cancel
                            </Button>
                        )}
                    </div>
                </CardHeader>

                <CardContent className="space-y-4 overflow-hidden">
                    {/* Error Alert */}
                    {workflowState.error && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="flex items-center justify-between">
                                <span>{workflowState.error}</span>
                                <Button variant="outline" size="sm" onClick={handleRetry}>
                                    Retry
                                </Button>
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* Status Message and Timeline */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between gap-4">
                            <StatusMessage status={workflowState.status} />
                        </div>

                        <ProgressTimeline status={workflowState.status} />
                    </div>

                    {/* Mood Analysis Display */}
                    <MoodAnalysisDisplay
                        moodAnalysis={workflowState.moodAnalysis}
                        moodPrompt={workflowState.moodPrompt}
                    />

                    {/* Workflow Insights */}
                    <WorkflowInsights
                        status={workflowState.status}
                        moodAnalysis={workflowState.moodAnalysis}
                        recommendations={workflowState.recommendations}
                        metadata={workflowState.metadata}
                        error={workflowState.error}
                    />

                    {/* Completion Actions */}
                    {workflowState.status === 'completed' && workflowState.playlist && (
                        <div className="flex gap-2 pt-2">
                            <Button variant="outline" onClick={handleCancelClick}>
                                Start New
                            </Button>
                        </div>
                    )}

                    {workflowState.status === 'failed' && (
                        <div className="flex gap-2 pt-2">
                            <Button onClick={handleRetry} className="flex-1">
                                Try Again
                            </Button>
                            <Button variant="outline" onClick={handleCancelClick}>
                                Cancel
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            <CancelWorkflowDialog
                open={showCancelDialog}
                onOpenChange={setShowCancelDialog}
                onConfirm={handleConfirmCancel}
                isCancelling={isCancelling}
            />
        </>
    );
}

