'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { AlertCircle, CheckCircle, Loader2, Music, XCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface WorkflowProgressProps {
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export default function WorkflowProgress({ onComplete, onError }: WorkflowProgressProps) {
  const router = useRouter();
  const { workflowState, startWorkflow, stopWorkflow, clearError } = useWorkflow();

  // Define workflow stages
  const workflowStages = [
    { key: 'analyzing_mood', label: 'Analyzing mood' },
    { key: 'gathering_seeds', label: 'Finding seeds' },
    { key: 'generating_recommendations', label: 'Generating playlist' },
    { key: 'evaluating_quality', label: 'Evaluating' },
    { key: 'optimizing_recommendations', label: 'Optimizing' },
    { key: 'creating_playlist', label: 'Creating playlist' },
    { key: 'completed', label: 'Complete' },
  ];

  // Get current stage index
  const getCurrentStageIndex = (status: string | null): number => {
    if (!status) return 0;
    const index = workflowStages.findIndex(stage => status.includes(stage.key));
    return index >= 0 ? index : 0;
  };

  // Get visible stages (current + 2 previous)
  const getVisibleStages = () => {
    const currentIndex = getCurrentStageIndex(workflowState.status);
    const startIndex = Math.max(0, currentIndex - 2);
    const endIndex = currentIndex + 1;
    return workflowStages.slice(startIndex, endIndex);
  };

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'analyzing_mood':
      case 'gathering_seeds':
      case 'generating_recommendations':
      case 'evaluating_quality':
      case 'optimizing_recommendations':
      case 'processing_edits':
      case 'creating_playlist':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'awaiting_user_input':
        return <Music className="w-4 h-4" />;
      default:
        return <Music className="w-4 h-4" />;
    }
  };

  const getStatusMessage = (status: string | null, currentStep?: string) => {
    // Check for iteration-based steps
    if (currentStep?.includes('iteration')) {
      const match = currentStep.match(/iteration[_\s](\d+)/i);
      const iteration = match ? match[1] : '1';

      if (currentStep.includes('evaluating_quality')) {
        return `🔍 Evaluating playlist quality (${iteration}/3)...`;
      }
      if (currentStep.includes('optimizing_recommendations')) {
        return `✨ Optimizing recommendations (${iteration}/3)...`;
      }
    }

    switch (status) {
      case 'analyzing_mood':
        return '🤔 Analyzing your mood...';
      case 'gathering_seeds':
        return '🎵 Finding your music preferences...';
      case 'generating_recommendations':
        return '🎼 Generating perfect recommendations...';
      case 'evaluating_quality':
        return '🔍 Evaluating playlist quality...';
      case 'optimizing_recommendations':
        return '✨ Optimizing your playlist...';
      case 'awaiting_user_input':
        return '✏️ Ready for editing!';
      case 'processing_edits':
        return '🔄 Processing your changes...';
      case 'creating_playlist':
        return '🎵 Creating your Spotify playlist...';
      case 'completed':
        return '🎉 Playlist created successfully!';
      case 'failed':
        return '❌ Something went wrong';
      default:
        return '🎵 Starting workflow...';
    }
  };


  const handleRetry = () => {
    clearError();
    // The workflow will automatically restart polling
  };

  const handleStop = () => {
    stopWorkflow();
    router.push('/create');
  };

  if (!workflowState.sessionId && !workflowState.isLoading) {
    return null;
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            {getStatusIcon(workflowState.status)}
            Playlist Generation
          </CardTitle>
          {workflowState.sessionId && workflowState.status !== 'completed' && workflowState.status !== 'failed' && (
            <Button variant="outline" size="sm" onClick={handleStop}>
              Cancel
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
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

        {/* Timeline with Dots */}
        <div className="space-y-4">
          <div className="text-sm font-medium">
            {getStatusMessage(workflowState.status, workflowState.currentStep)}
          </div>

          {/* Enhanced Dot Timeline */}
          <div className="relative">
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-gradient-to-r from-muted/30 to-muted/10 backdrop-blur-sm border border-border/50">
              {getVisibleStages().map((stage, index) => {
                const isCurrentStage = workflowState.status?.includes(stage.key);
                const isPreviousStage = index < getVisibleStages().length - 1;

                return (
                  <div key={stage.key} className="flex items-center gap-3">
                    <div className="relative flex items-center justify-center">
                      {/* Glow effect for current stage */}
                      {isCurrentStage && (
                        <div className="absolute w-6 h-6 bg-primary/20 rounded-full animate-ping" />
                      )}
                      {/* Main dot */}
                      <div
                        className={cn(
                          "rounded-full transition-all duration-500 relative z-10",
                          isCurrentStage
                            ? "w-4 h-4 bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/50 ring-2 ring-primary/30 ring-offset-2 ring-offset-background"
                            : "w-2.5 h-2.5 bg-gradient-to-br from-muted-foreground/60 to-muted-foreground/40"
                        )}
                      />
                    </div>
                    {index < getVisibleStages().length - 1 && (
                      <div className={cn(
                        "h-0.5 w-8 rounded-full transition-all duration-300",
                        isCurrentStage
                          ? "bg-gradient-to-r from-primary/60 to-muted-foreground/20"
                          : "bg-muted-foreground/20"
                      )} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Current Step */}
        {workflowState.currentStep && (
          <div className="text-sm text-muted-foreground">
            <span className="font-medium">Current step:</span> {workflowState.currentStep}
          </div>
        )}

        {/* Mood Prompt */}
        {workflowState.moodPrompt && (
          <div className="text-sm">
            <span className="font-medium">Mood:</span> {workflowState.moodPrompt}
          </div>
        )}

        {/* Completion Actions */}
        {workflowState.status === 'completed' && workflowState.playlist && (
          <div className="flex gap-2 pt-2">
            <Button onClick={onComplete} className="flex-1">
              View Playlist
            </Button>
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