'use client';

import { AuthGuard } from '@/components/AuthGuard';
import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodInput from '@/components/MoodInput';
import { AILoadingSpinner } from '@/components/shared/LoadingStates';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';
import { Suspense, useEffect, useState } from 'react';
import { useCreatePageLogic } from '@/lib/hooks';
import { CreatePageLayout } from '@/components/features/create/layout/CreatePageLayout';
import { CreatePageHeader } from '@/components/features/create/layout/CreatePageHeader';
import { QuotaDisplay } from '@/components/features/create/inputs/QuotaDisplay';

const PlaylistEditor = dynamic(() => import('@/components/PlaylistEditor'), {
  loading: () => <EditorSkeleton />,
  ssr: false,
});

const PlaylistResults = dynamic(() => import('@/components/PlaylistResults'), {
  loading: () => <ResultsSkeleton />,
});

function EditorSkeleton() {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <div className="animate-pulse w-full max-w-2xl space-y-4">
        <div className="h-8 bg-muted rounded" />
        <div className="h-40 bg-muted rounded" />
        <div className="h-8 bg-muted rounded" />
      </div>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="animate-pulse w-full max-w-xl space-y-4">
        <div className="h-6 bg-muted rounded" />
        <div className="h-6 bg-muted rounded" />
        <div className="h-6 bg-muted rounded" />
      </div>
    </div>
  );
}

// Main content component that uses workflow context
function CreatePageContent() {
  const {
    selectedMood,
    showLoginDialog,
    setShowLoginDialog,
    workflowState,
    handleMoodSubmit,
    handleEditComplete,
    handleEditCancel,
  } = useCreatePageLogic();

  const [quotaLoading, setQuotaLoading] = useState(true);
  const [contentVisible, setContentVisible] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setContentVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const entryAnimation = cn(
    'transform-gpu transition-all duration-700 ease-out',
    contentVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
  );

  // Show editor if workflow is awaiting user input
  if (workflowState.awaitingInput && workflowState.recommendations.length > 0 && workflowState.sessionId) {
    return (
      <CreatePageLayout>
        <div className={entryAnimation}>
          <PlaylistEditor
            sessionId={workflowState.sessionId}
            recommendations={workflowState.recommendations}
            onSave={handleEditComplete}
            onCancel={handleEditCancel}
          />
        </div>
      </CreatePageLayout>
    );
  }

  // Show results if workflow is completed
  if (workflowState.status === 'completed' && workflowState.recommendations.length > 0) {
    return (
      <CreatePageLayout>
        <div className={entryAnimation}>
          <PlaylistResults />
        </div>
      </CreatePageLayout>
    );
  }

  return (
    <CreatePageLayout>
      {/* Login Dialog */}
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

      <div className={entryAnimation}>
        <CreatePageHeader />

        {/* Loading Spinner - show while waiting for session redirect */}
        {/* Only show when we're starting a new workflow, not during cleanup */}
        {workflowState.isLoading && !workflowState.sessionId && workflowState.moodPrompt && (
          <AILoadingSpinner />
        )}

        {/* Mood Input - only show if no active workflow */}
        {!workflowState.sessionId && (
          <div className="flex justify-center">
            <div className="w-full max-w-md space-y-3">
              <div className={workflowState.isLoading ? 'hidden' : ''}>
                <QuotaDisplay onLoadingChange={setQuotaLoading} />
              </div>
              {!workflowState.isLoading && (
                <MoodInput
                  onSubmit={handleMoodSubmit}
                  initialMood={selectedMood || undefined}
                  loading={quotaLoading}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </CreatePageLayout>
  );
}

function CreatePageWithAuth() {
  return (
    <AuthGuard optimistic={true}>
      <CreatePageContent />
    </AuthGuard>
  );
}

export default function CreatePage() {
  return (
    <Suspense fallback={
      <div className="relative h-screen overflow-hidden bg-gradient-to-br from-background via-background/90 to-background">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div
            aria-hidden="true"
            className="absolute left-[-18%] top-[-18%] h-[36rem] w-[36rem] rounded-full bg-primary/25 blur-[130px] opacity-70"
          />
          <div
            aria-hidden="true"
            className="absolute right-[-20%] bottom-[-25%] h-[32rem] w-[32rem] rounded-full bg-muted/40 blur-[150px] opacity-70"
          />
        </div>
        <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
          <DotPattern
            className={cn(
              "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
              "text-muted-foreground/10"
            )}
          />
        </div>
        <div className="flex h-screen items-center justify-center px-6">
          <div className="w-full max-w-lg rounded-3xl border border-border/40 bg-background/80 p-10 text-center shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
            <AILoadingSpinner title="Loading..." subtitle="Setting up your experience" />
          </div>
        </div>
      </div>
    }>
      <CreatePageWithAuth />
    </Suspense>
  );
}
