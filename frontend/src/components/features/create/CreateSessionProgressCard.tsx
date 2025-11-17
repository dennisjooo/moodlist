'use client';

import { AnchorTracksDisplay } from '@/components/features/workflow/AnchorTracksDisplay';
import { CancelWorkflowDialog } from '@/components/features/workflow/CancelWorkflowDialog';
import { MoodAnalysisDisplay } from '@/components/features/workflow/MoodAnalysisDisplay';
import { ProgressTimeline } from '@/components/features/workflow/ProgressTimeline';
import { StatusIcon } from '@/components/features/workflow/StatusIcon';
import { StatusMessage } from '@/components/features/workflow/StatusMessage';
import { UpdatePulse } from '@/components/features/workflow/UpdatePulse';
import { WorkflowInsights } from '@/components/features/workflow/WorkflowInsights';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { useWorkflowCancellation } from '@/lib/hooks';
import type { Track, AnchorTrack } from '@/lib/types/workflow';
import { cn } from '@/lib/utils';
import { AlertCircle, Music, Sparkles, Star } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface TrackCardProps {
  track: Track;
  index: number;
  isNew: boolean;
}

function TrackCard({ track, index, isNew }: TrackCardProps) {
  return (
    <div
      key={track.track_id}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border border-border/40',
        'bg-gradient-to-br from-card via-card/95 to-card/90',
        'transition-all duration-300 hover:shadow-sm hover:border-border/60',
        isNew && 'animate-in slide-in-from-top-2 fade-in duration-500'
      )}
    >
      {/* Track Number */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 flex items-center justify-center text-sm font-semibold">
        {index + 1}
      </div>

      {/* Track Info */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
        <p className="text-xs text-muted-foreground truncate">
          {track.artists.join(', ')}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
            <span className="text-xs text-muted-foreground">
              {Math.round(track.confidence_score * 30 + 70)}%
            </span>
          </div>
          {track.source && (
            <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-border/40">
              {track.source}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

interface RightPanelProps {
  tracks: Track[];
  showAnchors: boolean;
  anchorTracks: AnchorTrack[] | undefined;
}

function RightPanel({ tracks, showAnchors, anchorTracks }: RightPanelProps) {
  const [previousCount, setPreviousCount] = useState(0);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  // Track when new tracks are added
  useEffect(() => {
    if (tracks.length > previousCount) {
      setPreviousCount(tracks.length);

      // Auto-scroll to bottom when new tracks arrive
      if (shouldAutoScroll.current && scrollAreaRef.current) {
        const scrollElement = scrollAreaRef.current.querySelector(
          '[data-radix-scroll-area-viewport]'
        );
        if (scrollElement) {
          setTimeout(() => {
            scrollElement.scrollTo({
              top: scrollElement.scrollHeight,
              behavior: 'smooth',
            });
          }, 100);
        }
      }
    }
  }, [tracks.length, previousCount]);

  // Detect manual scrolling to disable auto-scroll
  useEffect(() => {
    const scrollElement = scrollAreaRef.current?.querySelector(
      '[data-radix-scroll-area-viewport]'
    );
    if (!scrollElement) return;

    const handleScroll = () => {
      const isNearBottom =
        scrollElement.scrollHeight -
        scrollElement.scrollTop -
        scrollElement.clientHeight <
        100;
      shouldAutoScroll.current = isNearBottom;
    };

    scrollElement.addEventListener('scroll', handleScroll);
    return () => scrollElement.removeEventListener('scroll', handleScroll);
  }, []);

  const showTracks = tracks.length > 0;

  // Show anchor tracks when available and no recommendations yet
  if (showAnchors && anchorTracks && anchorTracks.length > 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-3 px-1 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">Foundation Tracks</h3>
          </div>
          <Badge variant="outline" className="text-xs border-border/40">
            {anchorTracks.length} {anchorTracks.length === 1 ? 'track' : 'tracks'}
          </Badge>
        </div>

        <ScrollArea className="h-[400px]">
          <div className="space-y-2 p-2 pr-4">
            {anchorTracks.map((track, index) => (
              <div
                key={`${track.id}-${index}`}
                className="group flex items-center gap-3 rounded-lg border border-border/40 bg-gradient-to-r from-muted/40 to-muted/20 hover:from-muted/50 hover:to-muted/30 px-3.5 py-2.5 animate-in fade-in duration-300 transition-all hover:shadow-sm hover:border-border/60"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-foreground truncate transition-colors">
                    {track.name}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {track.artists.join(', ')}
                  </p>
                  {track.albumName && (
                    <p className="text-[10px] text-muted-foreground/70 truncate mt-0.5">
                      {track.albumName}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  {track.user_mentioned && (
                    <Badge variant="secondary" className="text-[10px] px-2 py-0.5 bg-primary/10 border-primary/20 font-medium">
                      Your pick
                    </Badge>
                  )}
                  {track.anchor_type === 'genre' && !track.user_mentioned && (
                    <Badge variant="outline" className="text-[10px] px-2 py-0.5 border-border/50 bg-muted/50 font-medium">
                      Genre fit
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    );
  }

  if (!showTracks) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-center px-4">
        <div className="rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 p-6 mb-4">
          <Music className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-base font-semibold mb-2">Gathering tracks...</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Your personalized playlist is being crafted. Tracks will appear here
          as they&apos;re discovered.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-3 px-1 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold">Live Tracks</h3>
        </div>
        <Badge variant="outline" className="text-xs border-border/40">
          {tracks.length} {tracks.length === 1 ? 'track' : 'tracks'}
        </Badge>
      </div>

      <ScrollArea
        ref={scrollAreaRef}
        className="h-[400px]"
      >
        <div className="space-y-2 p-2 pr-4">
          {tracks.map((track, index) => (
            <TrackCard
              key={track.track_id}
              track={track}
              index={index}
              isNew={index >= previousCount - 1}
            />
          ))}
        </div>
      </ScrollArea>

      <div className="flex items-center justify-center text-xs text-muted-foreground gap-2 pt-3">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Listening for new tracks...
      </div>
    </div>
  );
}

export function CreateSessionProgressCard() {
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
  const showTracks = workflowState.recommendations.length > 0;
  const showAnchors = Boolean(
    workflowState.anchorTracks &&
    workflowState.anchorTracks.length > 0 &&
    workflowState.recommendations.length === 0
  );

  const showRightPanel = showTracks || showAnchors || isActive;

  return (
    <>
      <Card
        className={cn(
          'w-full overflow-hidden transition-all duration-300',
          'border-border/60 shadow-sm hover:shadow-md',
          'bg-gradient-to-br from-card via-card to-card/95',
          isCancelling && 'opacity-60 pointer-events-none'
        )}
      >
        <CardHeader className="pb-4 border-b border-border/40 bg-gradient-to-r from-muted/20 to-transparent space-y-3">
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

          {/* Status Message and Timeline */}
          <div className="space-y-3">
            <StatusMessage
              status={workflowState.status}
              currentStep={workflowState.currentStep}
            />
            <ProgressTimeline status={workflowState.status} />
          </div>
        </CardHeader>

        <CardContent className="pt-4">
          <div className={cn('grid gap-6', showRightPanel ? 'lg:grid-cols-2' : 'grid-cols-1')}>
            {/* Left Panel: Workflow Progress */}
            <div className="space-y-4">
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
            </div>

            {/* Right Panel: Anchor Tracks or Live Tracks */}
            {showRightPanel && (
              <div className="lg:border-l lg:border-border/30 lg:pl-6">
                <RightPanel
                  tracks={workflowState.recommendations}
                  showAnchors={showAnchors}
                  anchorTracks={workflowState.anchorTracks}
                />
              </div>
            )}
          </div>
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
