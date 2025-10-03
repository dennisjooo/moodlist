'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import { AlertCircle, CheckCircle, Loader2, Music, XCircle, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface WorkflowProgressProps {
  onComplete?: () => void;
  onError?: (error: string) => void;
}

// Fun music facts to keep users entertained
const MUSIC_FACTS = [
  "Spotify has over 100 million tracks in its library!",
  "The average person listens to about 18 hours of music per week.",
  "Music can reduce stress and improve your mood instantly.",
  "Your heartbeat can sync to the rhythm of music you're listening to.",
  "Studies show music helps you focus and be more productive.",
  "The fastest tempo in classical music can reach over 200 BPM!",
  "Listening to music releases dopamine, the 'feel-good' hormone.",
  "90% of people report music helps them deal with emotions.",
  "Your music taste is as unique as your fingerprint.",
  "The right playlist can make your workout feel 15% easier!",
];

export default function WorkflowProgress({ onComplete, onError }: WorkflowProgressProps) {
  const router = useRouter();
  const { workflowState, startWorkflow, stopWorkflow, clearError } = useWorkflow();
  const [currentFactIndex, setCurrentFactIndex] = useState(0);

  // Rotate fun facts every 6 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFactIndex((prev) => (prev + 1) % MUSIC_FACTS.length);
    }, 6000);
    return () => clearInterval(interval);
  }, []);

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
    switch (status) {
      case 'analyzing_mood':
        return '🤔 Analyzing your mood and finding the perfect vibe...';
      case 'gathering_seeds':
        return '🎵 Diving into your music library to understand your taste...';
      case 'generating_recommendations':
        return '🎼 Handpicking the perfect tracks just for you...';
      case 'evaluating_quality':
        return '🔍 Making sure every track fits your mood perfectly...';
      case 'optimizing_recommendations':
        return '✨ Fine-tuning your playlist for the best flow...';
      case 'awaiting_user_input':
        return '✏️ Ready for your creative touch!';
      case 'processing_edits':
        return '🔄 Applying your changes with care...';
      case 'creating_playlist':
        return '🎵 Saving your personalized playlist to Spotify...';
      case 'completed':
        return '🎉 Your perfect playlist is ready to play!';
      case 'failed':
        return '❌ Oops, something went wrong';
      default:
        return '🎵 Getting everything ready for you...';
    }
  };

  // Calculate progress percentage
  const getProgressPercentage = () => {
    const currentIndex = getCurrentStageIndex(workflowState.status);
    const totalStages = workflowStages.length - 1; // Exclude completed
    return Math.round((currentIndex / totalStages) * 100);
  };


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
        console.log('Workflow cancelled on backend');
      } catch (error) {
        console.error('Failed to cancel workflow on backend:', error);
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

  return (
    <Card className="w-full overflow-hidden">
      <CardHeader className="pb-3 overflow-hidden">
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

        {/* Timeline with Dots */}
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm font-medium flex-1">
              {getStatusMessage(workflowState.status, workflowState.currentStep)}
            </div>
            {workflowState.status && workflowState.status !== 'completed' && workflowState.status !== 'failed' && (
              <div className="text-xs text-muted-foreground whitespace-nowrap">
                {getProgressPercentage()}%
              </div>
            )}
          </div>

          {/* Enhanced Dot Timeline */}
          <div className="relative">
            <div className="flex items-center justify-between px-2 py-3 rounded-lg bg-gradient-to-r from-muted/30 to-muted/10 backdrop-blur-sm border border-border/50">
              {getVisibleStages().map((stage, index) => {
                const isCurrentStage = workflowState.status?.includes(stage.key);

                return (
                  <div key={stage.key} className="flex items-center flex-1">
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
                        "h-0.5 flex-1 rounded-full transition-all duration-300 ml-2",
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

        {/* Mood Analysis - Show when available */}
        {workflowState.moodAnalysis && (
          <div className="space-y-3 rounded-lg bg-muted/30 p-3 sm:p-4 border border-border/50 overflow-hidden">
            <div className="flex items-start gap-2 overflow-hidden">
              <div className="text-xl sm:text-2xl flex-shrink-0 mt-0.5">🎵</div>
              <div className="flex-1 space-y-3 min-w-0 overflow-hidden">
                <p className="text-sm font-medium text-foreground break-words leading-relaxed pr-2 [word-break:break-word] max-w-full">
                  {workflowState.moodAnalysis.mood_interpretation}
                </p>
                {workflowState.moodAnalysis.primary_emotion && (
                  <div className="flex items-center flex-wrap gap-2 text-xs text-muted-foreground pt-1">
                    <Badge variant="secondary" className="text-xs">
                      {workflowState.moodAnalysis.primary_emotion}
                    </Badge>
                    {workflowState.moodAnalysis.energy_level && (
                      <Badge variant="secondary" className="text-xs">
                        {workflowState.moodAnalysis.energy_level}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Mood Prompt - Show when no analysis yet */}
        {workflowState.moodPrompt && !workflowState.moodAnalysis && (
          <div className="text-sm">
            <span className="font-medium">Mood:</span> {workflowState.moodPrompt}
          </div>
        )}

        {/* Workflow Insights - Show actual data about what we're doing */}
        {workflowState.status &&
          workflowState.status !== 'completed' &&
          workflowState.status !== 'failed' &&
          !workflowState.error && (
            <div className="rounded-lg bg-gradient-to-r from-primary/5 to-purple-500/5 p-3 sm:p-4 border border-primary/10 overflow-hidden">
              <div className="flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">What we're cooking:</p>

                  {/* Show different insights based on workflow stage */}
                  {workflowState.status === 'analyzing_mood' && (
                    <p className="text-sm text-foreground">
                      Analyzing your mood description and musical preferences...
                    </p>
                  )}

                  {workflowState.status === 'gathering_seeds' && (
                    <div className="space-y-1">
                      {workflowState.moodAnalysis?.primary_emotion ? (
                        <>
                          <p className="text-sm text-foreground">
                            Searching for tracks that match: <span className="font-medium">{workflowState.moodAnalysis.primary_emotion}</span> vibes
                          </p>
                          {workflowState.moodAnalysis.search_keywords && workflowState.moodAnalysis.search_keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {workflowState.moodAnalysis.search_keywords.slice(0, 4).map((keyword, idx) => (
                                <span key={idx} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-sm text-foreground">
                          Finding the perfect seed tracks to build your playlist...
                        </p>
                      )}
                    </div>
                  )}

                  {workflowState.status === 'generating_recommendations' && (
                    <div className="space-y-1.5">
                      {workflowState.recommendations && workflowState.recommendations.length > 0 ? (
                        <p className="text-sm text-foreground flex items-center gap-2">
                          <Music className="w-3.5 h-3.5" />
                          <span>Found <span className="font-medium">{workflowState.recommendations.length}</span> perfect tracks</span>
                        </p>
                      ) : (
                        <p className="text-sm text-foreground">
                          Handpicking tracks that perfectly match your vibe...
                        </p>
                      )}
                    </div>
                  )}

                  {workflowState.status === 'evaluating_quality' && (
                    <div className="space-y-1.5">
                      {workflowState.recommendations && workflowState.recommendations.length > 0 && (
                        <p className="text-sm text-foreground flex items-center gap-2">
                          <Music className="w-3.5 h-3.5" />
                          <span>Evaluating <span className="font-medium">{workflowState.recommendations.length}</span> tracks</span>
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        Checking that every track flows perfectly together...
                      </p>
                    </div>
                  )}

                  {workflowState.status === 'optimizing_recommendations' && (
                    <div className="space-y-1.5">
                      {workflowState.recommendations && workflowState.recommendations.length > 0 && (
                        <p className="text-sm text-foreground flex items-center gap-2">
                          <Music className="w-3.5 h-3.5" />
                          <span>Refining <span className="font-medium">{workflowState.recommendations.length}</span> tracks</span>
                        </p>
                      )}
                      {workflowState.metadata?.iteration ? (
                        <p className="text-sm text-muted-foreground">
                          Optimization pass {workflowState.metadata.iteration} - Making it even better!
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Fine-tuning the playlist for the best flow...
                        </p>
                      )}
                    </div>
                  )}

                  {workflowState.status === 'creating_playlist' && (
                    <p className="text-sm text-foreground">
                      Packaging {workflowState.recommendations?.length || 0} tracks into your personal Spotify playlist...
                    </p>
                  )}

                  {/* Fallback for pending or unknown states */}
                  {workflowState.status === 'pending' && (
                    <p className="text-sm text-foreground">
                      Preparing your personalized playlist experience...
                    </p>
                  )}

                  {/* Show fun fact for any other state */}
                  {!['analyzing_mood', 'gathering_seeds', 'generating_recommendations',
                    'evaluating_quality', 'optimizing_recommendations', 'creating_playlist', 'pending'].includes(workflowState.status || '') && (
                      <p
                        key={currentFactIndex}
                        className="text-sm text-foreground animate-in fade-in duration-500"
                      >
                        {MUSIC_FACTS[currentFactIndex]}
                      </p>
                    )}
                </div>
              </div>
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