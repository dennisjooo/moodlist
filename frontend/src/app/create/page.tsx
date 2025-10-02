'use client';

import MoodCard from '@/components/MoodCard';
import MoodInput from '@/components/MoodInput';
import Navigation from '@/components/Navigation';
import PlaylistEditor from '@/components/PlaylistEditor';
import PlaylistResults from '@/components/PlaylistResults';
import { Badge } from '@/components/ui/badge';
import { DotPattern } from '@/components/ui/dot-pattern';
import WorkflowProgress from '@/components/WorkflowProgress';
import { cn } from '@/lib/utils';
import { getMoodGenre } from '@/lib/moodColors';
import { useWorkflow } from '@/lib/workflowContext';
import { Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Main content component that uses workflow context
function CreatePageContent() {
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);
  const { workflowState, startWorkflow, resetWorkflow } = useWorkflow();

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Clear any existing workflow state on mount to start fresh
  useEffect(() => {
    if (workflowState.sessionId && !workflowState.isLoading) {
      // User navigated to /create with an old session, clear it
      resetWorkflow();
    }
  }, []); // Only run on mount

  // Redirect to dynamic route when session_id is available after starting new workflow
  useEffect(() => {
    if (workflowState.sessionId && workflowState.isLoading) {
      router.push(`/create/${workflowState.sessionId}`);
    }
  }, [workflowState.sessionId, workflowState.isLoading, router]);

  const handleMoodSubmit = async (mood: string, genreHint?: string) => {
    try {
      await startWorkflow(mood, genreHint);
      // Note: Redirect happens in useEffect above when sessionId is set
    } catch (error) {
      console.error('Failed to start workflow:', error);
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

  const mobileMoods = [
    'Chill Evening',
    'Energetic Workout',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
  ];

  const desktopMoods = [
    'Chill Evening',
    'Energetic Workout',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
    'Rainy Day',
    'Party Vibes',
    'Happy Sunshine',
    'Melancholy Blues',
    'Adventure Time',
    'Cozy Winter',
  ];

  const moods = isMobile ? mobileMoods : desktopMoods;

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
        {workflowState.isLoading && !workflowState.sessionId && (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex flex-col items-center gap-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-primary rounded-full animate-bounce"></div>
                <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <p className="text-sm text-muted-foreground">Starting your playlist...</p>
            </div>
          </div>
        )}

        {/* Mood Input - only show if no active workflow */}
        {!workflowState.sessionId && !workflowState.isLoading && (
          <>
            <div className="flex justify-center">
              <div className="w-full max-w-md">
                <MoodInput onSubmit={handleMoodSubmit} />
              </div>
            </div>

            {/* Quick Mood Suggestions */}
            <div className="mt-16">
              <h2 className="text-2xl font-semibold text-center mb-8">Quick Suggestions</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
                {moods.map((mood, index) => (
                  <MoodCard
                    key={`${mood}-${index}`}
                    mood={mood}
                    onClick={() => handleMoodSubmit(mood, getMoodGenre(mood))}
                  />
                ))}
              </div>
            </div>
          </>
        )}

      </main>
    </div>
  );
}

export default function CreatePage() {
  return <CreatePageContent />;
}