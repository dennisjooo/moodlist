'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { useWorkflowCancellation } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';
import { AnchorTracksDisplay } from './AnchorTracksDisplay';
import { CancelWorkflowDialog } from './CancelWorkflowDialog';
import { MoodAnalysisDisplay } from './MoodAnalysisDisplay';
import { ProgressTimeline } from './ProgressTimeline';
import { StatusIcon } from './StatusIcon';
import { StatusMessage } from './StatusMessage';
import { UpdatePulse } from './UpdatePulse';
import { WorkflowInsights } from './WorkflowInsights';

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

    const handleRetry = () => {
        clearError();
        // The workflow will automatically restart polling
    };

    // Don't render if:
    // 1. No sessionId and not loading, OR
    // 2. Has sessionId but status is null (uninitialized state) and not loading
    if ((!workflowState.sessionId || workflowState.status === null) && !workflowState.isLoading) {
        return null;
    }

    const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';

    // Show anchor tracks when available and no recommendations yet
    const shouldShowAnchors =
        isActive &&
        workflowState.anchorTracks &&
        workflowState.anchorTracks.length > 0 &&
        workflowState.recommendations.length === 0;

    return (
        <>
            <Card className={cn(
                "w-full overflow-hidden transition-all duration-300",
                "border-border/60 shadow-sm hover:shadow-md",
                "bg-gradient-to-br from-card via-card to-card/95",
                isCancelling && "opacity-60 pointer-events-none"
            )}>
                <CardHeader className="pb-3 border-b border-border/40 bg-gradient-to-r from-muted/20 to-transparent">
                    <div className="flex items-center justify-between gap-3">
                        <CardTitle className="text-base flex items-center gap-2.5 font-semibold">
                            <StatusIcon status={workflowState.status} />
                            <span className="bg-gradient-to-br from-foreground to-foreground/80 bg-clip-text">
                                {isCancelling ? 'Cancelling...' : 'Playlist Generation'}
                            </span>
                            {isActive && (
                                <UpdatePulse
                                    triggerKey={`${workflowState.status}-${workflowState.currentStep}-${workflowState.recommendations.length}`}
                                    className="ml-0.5"
                                />
                            )}
                        </CardTitle>
                        {workflowState.sessionId && isActive && !isCancelling && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleCancelClick}
                                className="hover:bg-destructive/10 hover:text-destructive hover:border-destructive/50 transition-colors"
                            >
                                Cancel
                            </Button>
                        )}
                    </div>
                </CardHeader>

                <CardContent className="space-y-4 pt-4">
                    {/* Error Alert */}
                    {workflowState.error && (
                        <Alert variant="destructive" className="border-destructive/50 bg-destructive/5">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="flex items-center justify-between gap-3">
                                <span className="flex-1 text-sm">{workflowState.error}</span>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleRetry}
                                    className="shrink-0 border-destructive/30 hover:bg-destructive hover:text-destructive-foreground"
                                >
                                    Retry
                                </Button>
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* Status Message and Timeline */}
                    <div className="space-y-3.5 rounded-lg bg-gradient-to-br from-muted/30 via-muted/20 to-transparent p-4 border border-border/30">
                        <StatusMessage
                            status={workflowState.status}
                            currentStep={workflowState.currentStep}
                        />

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
                        currentStep={workflowState.currentStep}
                        moodAnalysis={workflowState.moodAnalysis}
                        recommendations={workflowState.recommendations}
                        anchorTracks={workflowState.anchorTracks}
                        metadata={workflowState.metadata}
                        error={workflowState.error}
                    />

                    {/* Anchor Tracks Display */}
                    {shouldShowAnchors && (
                        <AnchorTracksDisplay anchorTracks={workflowState.anchorTracks!} />
                    )}

                    {/* Action Buttons */}
                    {workflowState.status === 'completed' && workflowState.playlist && (
                        <div className="pt-2 border-t border-border/40">
                            <Button
                                variant="outline"
                                onClick={handleCancelClick}
                                className="w-full bg-gradient-to-r from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/20 border-primary/20 hover:border-primary/30 transition-all"
                            >
                                Start New Playlist
                            </Button>
                        </div>
                    )}

                    {workflowState.status === 'failed' && (
                        <div className="flex gap-3 pt-2 border-t border-border/40">
                            <Button
                                onClick={handleRetry}
                                className="flex-1 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-sm"
                            >
                                Try Again
                            </Button>
                            <Button
                                variant="outline"
                                onClick={handleCancelClick}
                                className="hover:bg-muted/50 transition-colors"
                            >
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

