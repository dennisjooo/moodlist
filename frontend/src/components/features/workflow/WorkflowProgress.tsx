'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { logger } from '@/lib/utils/logger';
import { AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { StatusIcon } from './StatusIcon';
import { StatusMessage } from './StatusMessage';
import { ProgressTimeline } from './ProgressTimeline';
import { MoodAnalysisDisplay } from './MoodAnalysisDisplay';
import { WorkflowInsights } from './WorkflowInsights';

export function WorkflowProgress() {
    const router = useRouter();
    const { workflowState, stopWorkflow, clearError } = useWorkflow();

    const handleRetry = () => {
        clearError();
        // The workflow will automatically restart polling
    };

    const handleStop = async () => {
        // Cancel the workflow on the backend if we have a session ID
        if (workflowState.sessionId) {
            try {
                const { workflowAPI } = await import('@/lib/workflowApi');
                await workflowAPI.cancelWorkflow(workflowState.sessionId);
                logger.info('Workflow cancelled on backend', { component: 'WorkflowProgress', sessionId: workflowState.sessionId });
            } catch (error) {
                logger.error('Failed to cancel workflow on backend', error, { component: 'WorkflowProgress', sessionId: workflowState.sessionId });
                // Continue with local cleanup even if backend call fails
            }
        }

        // Clean up local state and stop polling
        stopWorkflow();

        // Clear any errors that might be showing
        clearError();

        // Navigate to /create and force a clean state by using replace
        // This ensures we go back to the initial state with the mood input form
        router.replace('/create');
    };

    if (!workflowState.sessionId && !workflowState.isLoading) {
        return null;
    }

    const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';

    return (
        <Card className="w-full overflow-hidden">
            <CardHeader className="pb-3 overflow-hidden">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <StatusIcon status={workflowState.status} />
                        Playlist Generation
                    </CardTitle>
                    {workflowState.sessionId && isActive && (
                        <Button variant="outline" size="sm" onClick={handleStop}>
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
                        <Button variant="outline" onClick={handleStop}>
                            Start New
                        </Button>
                    </div>
                )}

                {workflowState.status === 'failed' && (
                    <div className="flex gap-2 pt-2">
                        <Button onClick={handleRetry} className="flex-1">
                            Try Again
                        </Button>
                        <Button variant="outline" onClick={handleStop}>
                            Cancel
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

