'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { AlertCircle, CheckCircle, Loader2, Music, XCircle } from 'lucide-react';

interface WorkflowProgressProps {
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export default function WorkflowProgress({ onComplete, onError }: WorkflowProgressProps) {
  const { workflowState, startWorkflow, stopWorkflow, clearError } = useWorkflow();

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

  const getProgressValue = (status: string | null, currentStep?: string) => {
    // Calculate progress for optimization iterations
    if (currentStep?.includes('iteration')) {
      const match = currentStep.match(/iteration[_\s](\d+)/i);
      const iteration = parseInt(match ? match[1] : '1');

      if (currentStep.includes('evaluating_quality')) {
        return 65 + (iteration * 3); // 68%, 71%, 74%
      }
      if (currentStep.includes('optimizing_recommendations')) {
        return 73 + (iteration * 4); // 77%, 81%, 85%
      }
    }

    switch (status) {
      case 'analyzing_mood':
        return 20;
      case 'gathering_seeds':
        return 40;
      case 'generating_recommendations':
        return 60;
      case 'evaluating_quality':
        return 70;
      case 'optimizing_recommendations':
        return 80;
      case 'awaiting_user_input':
        return 90;
      case 'processing_edits':
        return 92;
      case 'creating_playlist':
        return 95;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      default:
        return 0;
    }
  };

  const handleRetry = () => {
    clearError();
    // The workflow will automatically restart polling
  };

  const handleStop = () => {
    stopWorkflow();
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

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {getStatusMessage(workflowState.status, workflowState.currentStep)}
            </span>
            <Badge variant="outline" className="text-xs">
              {getProgressValue(workflowState.status, workflowState.currentStep)}%
            </Badge>
          </div>
          <Progress
            value={getProgressValue(workflowState.status, workflowState.currentStep)}
            className={cn(
              "h-2",
              workflowState.status === 'failed' && "bg-red-100"
            )}
          />
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