'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { AlertCircle, Music } from 'lucide-react';
import { MoodAnalysisDisplay } from './MoodAnalysisDisplay';
import { ProgressTimeline } from './ProgressTimeline';
import { StatusIcon } from './StatusIcon';
import { StatusMessage } from './StatusMessage';
import { WorkflowInsights } from './WorkflowInsights';
import { CancelWorkflowDialog } from './CancelWorkflowDialog';
import { PerceivedProgressBar } from './PerceivedProgressBar';
import { TrackCardSkeleton } from './TrackCardSkeleton';
import { UpdatePulse } from './UpdatePulse';
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

    // Don't render if:
    // 1. No sessionId and not loading, OR
    // 2. Has sessionId but status is null (uninitialized state) and not loading
    if ((!workflowState.sessionId || workflowState.status === null) && !workflowState.isLoading) {
        return null;
    }

    const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';

    const previewTracks = workflowState.recommendations.slice(0, 3);
    const anchorTracks = workflowState.anchorTracks?.slice(0, 3) || [];
    
    // Show anchor tracks when available and no recommendations yet
    const hasAnchors = anchorTracks.length > 0;
    const hasRecommendations = previewTracks.length > 0;
    
    const shouldShowSkeleton = Boolean(
        isActive &&
        !hasAnchors &&
        !hasRecommendations &&
        workflowState.status &&
        (
            workflowState.status.includes('gathering_seeds') ||
            workflowState.status.includes('generating_recommendations') ||
            workflowState.status.includes('evaluating_quality') ||
            workflowState.status.includes('optimizing_recommendations')
        )
    );

    return (
        <>
            <Card className={cn("w-full", isCancelling && "opacity-60 pointer-events-none")}>
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base flex items-center gap-2">
                            <StatusIcon status={workflowState.status} />
                            {isCancelling ? 'Cancelling...' : 'Playlist Generation'}
                            {isActive && (
                                <UpdatePulse
                                    triggerKey={`${workflowState.status}-${workflowState.currentStep}-${workflowState.recommendations.length}`}
                                    className="ml-1"
                                />
                            )}
                        </CardTitle>
                        {workflowState.sessionId && isActive && !isCancelling && (
                            <Button variant="outline" size="sm" onClick={handleCancelClick}>
                                Cancel
                            </Button>
                        )}
                    </div>
                </CardHeader>

                <CardContent className="space-y-3">
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
                    <div className="space-y-3">
                        <div className="flex items-center justify-between gap-4">
                            <StatusMessage
                                status={workflowState.status}
                                currentStep={workflowState.currentStep}
                            />
                        </div>

                        <ProgressTimeline status={workflowState.status} />
                        
                        {/* Perceived Progress Bar */}
                        {isActive && (
                            <PerceivedProgressBar
                                status={workflowState.status}
                                showPercentage={false}
                            />
                        )}
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

                    {/* Show anchor tracks when they're ready (before recommendations) */}
                    {hasAnchors && !hasRecommendations && isActive && (
                        <div className="rounded-lg border border-amber-500/30 bg-gradient-to-br from-amber-500/5 to-orange-500/5 p-3 space-y-3">
                            <div className="flex items-center justify-between">
                                <p className="text-xs uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300 font-medium">Foundation Tracks</p>
                                <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-700 dark:text-amber-300">
                                    Anchor
                                </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Hand-picked songs we&apos;re using as the blueprint for your vibe
                            </p>
                            <div className="space-y-2">
                                {anchorTracks.map((track, index) => (
                                    <div
                                        key={track.id || `${track.name}-${index}`}
                                        className="flex items-center gap-3 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 animate-in fade-in duration-300"
                                        style={{ animationDelay: `${index * 80}ms` }}
                                    >
                                        <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-md border border-amber-500/20 bg-amber-500/20">
                                            {track.albumCoverUrl ? (
                                                <img
                                                    src={track.albumCoverUrl}
                                                    alt={track.name || 'Anchor track cover art'}
                                                    className="h-full w-full object-cover"
                                                />
                                            ) : (
                                                <div className="flex h-full w-full items-center justify-center text-amber-700/80">
                                                    <Music className="h-5 w-5" />
                                                </div>
                                            )}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-semibold text-foreground truncate">
                                                {track.name}
                                            </p>
                                            <p className="text-xs text-muted-foreground truncate">
                                                {track.artists.join(', ')}
                                            </p>
                                            {track.albumName && (
                                                <p className="text-[10px] text-muted-foreground/70 truncate">
                                                    {track.albumName}
                                                </p>
                                            )}
                                        </div>
                                        <div className="flex flex-col items-end gap-1">
                                            {track.user_mentioned && (
                                                <Badge variant="secondary" className="text-[10px]">
                                                    Your pick
                                                </Badge>
                                            )}
                                            {track.anchor_type === 'genre' && !track.user_mentioned && (
                                                <Badge variant="outline" className="text-[10px] border-amber-500/40 text-amber-700 dark:text-amber-300">
                                                    Genre fit
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Perceived track loading (only when no anchors and no recommendations) */}
                    {shouldShowSkeleton && (
                        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-3">
                            <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                <span>Curating tracks</span>
                                <span className="normal-case tracking-normal text-[11px] text-muted-foreground/80">Your playlist is taking shape</span>
                            </div>
                            <TrackCardSkeleton count={3} />
                        </div>
                    )}

                    {/* Show recommendations when they arrive */}
                    {hasRecommendations && isActive && (
                        <div className="rounded-lg border border-border/50 bg-background/60 backdrop-blur-sm p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tracks already queued</p>
                                <span className="text-xs text-muted-foreground">
                                    {workflowState.recommendations.length} ready so far
                                </span>
                            </div>
                            <div className="space-y-2">
                                {previewTracks.map((track, index) => (
                                    <div
                                        key={track.track_id || `${track.track_name}-${index}`}
                                        className="flex items-center justify-between gap-3 rounded-md border border-border/50 bg-muted/30 px-3 py-2 animate-in fade-in duration-300"
                                        style={{ animationDelay: `${index * 80}ms` }}
                                    >
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium truncate">
                                                {track.track_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground truncate">
                                                {track.artists.join(', ')}
                                            </p>
                                        </div>
                                        <span className="text-[10px] font-semibold uppercase tracking-wide text-primary/80 bg-primary/10 px-2 py-1 rounded-full">
                                            New
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Completion Actions */}
                    {workflowState.status === 'completed' && workflowState.playlist && (
                        <div className="flex gap-2 pt-1">
                            <Button variant="outline" onClick={handleCancelClick}>
                                Start New
                            </Button>
                        </div>
                    )}

                    {workflowState.status === 'failed' && (
                        <div className="flex gap-2 pt-1">
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

