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
import { useEffect, useState } from 'react';

// Main content component that uses workflow context
function CreatePageContent() {
  const [isMobile, setIsMobile] = useState(false);
  const { workflowState, startWorkflow } = useWorkflow();

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleMoodSubmit = async (mood: string, genreHint?: string) => {
    try {
      await startWorkflow(mood, genreHint);
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

        {/* Workflow Progress */}
        {workflowState.isLoading && (
          <div className="mb-8">
            <WorkflowProgress />
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

        {/* Active Workflow Progress */}
        {workflowState.sessionId && workflowState.status !== 'completed' && (
          <div className="mb-8">
            <WorkflowProgress />
          </div>
        )}
      </main>
    </div>
  );
}

export default function CreatePage() {
  return <CreatePageContent />;
}