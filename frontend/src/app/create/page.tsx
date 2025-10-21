'use client';

import { AuthGuard } from '@/components/AuthGuard';
import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodInput from '@/components/MoodInput';
import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import PlaylistResults from '@/components/PlaylistResults';
import { Badge } from '@/components/ui/badge';
import { DotPattern } from '@/components/ui/dot-pattern';
import { useAuth } from '@/lib/authContext';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { useWorkflow } from '@/lib/workflowContext';
import { Sparkles } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

// Main content component that uses workflow context
function CreatePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuth();
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [showLoginDialog, setShowLoginDialog] = useState(false);
  const { workflowState, startWorkflow, resetWorkflow } = useWorkflow();

  // Get mood from URL params if present
  useEffect(() => {
    const moodParam = searchParams.get('mood');
    if (moodParam) {
      setSelectedMood(moodParam);
    }
  }, [searchParams]);

  // Clear any existing workflow state on mount to start fresh
  // This ensures that when user navigates to /create (e.g., via cancel button),
  // the page shows the initial mood input form
  useEffect(() => {
    // If there's a session ID when mounting /create (not /create/[id]),
    // it means we're coming from a cancelled workflow or navigating back
    // Clear it to show a fresh state
    if (workflowState.sessionId) {
      logger.debug('Clearing workflow state on /create mount', { component: 'CreatePage' });
      resetWorkflow();
    }
  }, []);


  // Also clear workflow state when it changes while on /create page
  // This handles cases where user stops workflow while already on /create
  useEffect(() => {
    // Only reset if we're on the base /create page (not /create/[id])
    // and we have a session ID (indicating a workflow was stopped)
    const isBaseCreatePage = !window.location.pathname.includes('/create/') ||
      window.location.pathname === '/create';

    if (isBaseCreatePage && workflowState.sessionId) {
      logger.debug('Clearing workflow state due to session presence on /create', { component: 'CreatePage' });
      resetWorkflow();
    }
  }, [workflowState.sessionId, resetWorkflow]);

  // Redirect to dynamic route when session_id is available after starting new workflow
  useEffect(() => {
    if (workflowState.sessionId && workflowState.isLoading) {
      router.push(`/create/${workflowState.sessionId}`);
    }
  }, [workflowState.sessionId, workflowState.isLoading, router]);

  const handleMoodSubmit = async (mood: string, genreHint?: string) => {
    // Check if user is authenticated before starting workflow
    if (!isAuthenticated) {
      setShowLoginDialog(true);
      return;
    }

    try {
      await startWorkflow(mood, genreHint);
      // Note: Redirect happens in useEffect above when sessionId is set
    } catch (error) {
      logger.error('Failed to start workflow', error, { component: 'CreatePage' });
    }
  };


  const handleEditComplete = () => {
    // Refresh the page to show final results
    window.location.reload();
  };

  const handleEditCancel = () => {
    // Go back to results view
    window.location.reload();
  };

  // Show editor if workflow is awaiting user input
  if (workflowState.awaitingInput && workflowState.recommendations.length > 0 && workflowState.sessionId) {
    return (
      <div className="min-h-screen bg-background relative">
        <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
          <DotPattern
            className={cn(
              "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
            )}
          />
        </div>

        <Navigation />

        <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <PlaylistEditor
            sessionId={workflowState.sessionId}
            recommendations={workflowState.recommendations}
            onSave={handleEditComplete}
            onCancel={handleEditCancel}
          />
        </main>
      </div>
    );
  }

  // Show results if workflow is completed
  if (workflowState.status === 'completed' && workflowState.recommendations.length > 0) {
    return (
      <div className="min-h-screen bg-background relative">
        <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
          <DotPattern
            className={cn(
              "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
            )}
          />
        </div>

        <Navigation />

        <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <PlaylistResults />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative">
      {/* Login Dialog */}
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

      {/* Fixed Dot Pattern Background */}
      <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
          )}
        />
      </div>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
            <Sparkles className="w-4 h-4" />
            AI-Powered Playlist Creation
          </Badge>

          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
            What's your mood?
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Describe how you're feeling and our AI will create the perfect Spotify playlist for your moment.
          </p>
        </div>

        {/* Loading Spinner - show while waiting for session redirect */}
        {/* Only show when we're starting a new workflow, not during cleanup */}
        {workflowState.isLoading && !workflowState.sessionId && workflowState.moodPrompt && (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex flex-col items-center gap-6">
              {/* Animated musical notes */}
              <div className="relative w-24 h-24">
                {/* Spinning ring */}
                <div className="absolute inset-0 rounded-full border-4 border-primary/20 animate-pulse"></div>
                <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin"></div>

                {/* Center icon */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-primary animate-pulse" />
                </div>

                {/* Floating musical notes */}
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '0s', animationDuration: '2s' }}>
                  <span className="text-xs">♪</span>
                </div>
                <div className="absolute -bottom-2 -left-2 w-5 h-5 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '0.5s', animationDuration: '2.5s' }}>
                  <span className="text-xs">♫</span>
                </div>
                <div className="absolute top-1/2 -right-4 w-4 h-4 bg-primary/20 rounded-full flex items-center justify-center animate-bounce" style={{ animationDelay: '1s', animationDuration: '2s' }}>
                  <span className="text-xs">♪</span>
                </div>
              </div>

              {/* Loading text with gradient */}
              <div className="text-center space-y-2">
                <p className="text-lg font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent animate-pulse">
                  Firing up the AI...
                </p>
                <p className="text-sm text-muted-foreground">
                  Preparing to analyze your vibe
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Mood Input - only show if no active workflow */}
        {!workflowState.sessionId && !workflowState.isLoading && (
          <div className="flex justify-center">
            <div className="w-full max-w-md">
              <MoodInput onSubmit={handleMoodSubmit} initialMood={selectedMood || undefined} />
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default function CreatePage() {
  return (
    <AuthGuard optimistic={true}>
      <CreatePageContent />
    </AuthGuard>
  );
}