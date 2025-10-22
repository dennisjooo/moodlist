'use client';

import { AuthGuard } from '@/components/AuthGuard';
import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodInput from '@/components/MoodInput';
import { AILoadingSpinner } from '@/components/shared/LoadingStates';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import { useCreatePageLogic } from '@/lib/hooks/useCreatePageLogic';
import { CreatePageLayout } from '@/components/features/create/CreatePageLayout';
import { CreatePageHeader } from '@/components/features/create/CreatePageHeader';

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

  // Show editor if workflow is awaiting user input
  if (workflowState.awaitingInput && workflowState.recommendations.length > 0 && workflowState.sessionId) {
    return (
      <CreatePageLayout>
        <PlaylistEditor
          sessionId={workflowState.sessionId}
          recommendations={workflowState.recommendations}
          onSave={handleEditComplete}
          onCancel={handleEditCancel}
        />
      </CreatePageLayout>
    );
  }

  // Show results if workflow is completed
  if (workflowState.status === 'completed' && workflowState.recommendations.length > 0) {
    return (
      <CreatePageLayout>
        <PlaylistResults />
      </CreatePageLayout>
    );
  }

  return (
    <CreatePageLayout>
      {/* Login Dialog */}
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

      <CreatePageHeader />

      {/* Loading Spinner - show while waiting for session redirect */}
      {/* Only show when we're starting a new workflow, not during cleanup */}
      {workflowState.isLoading && !workflowState.sessionId && workflowState.moodPrompt && (
        <AILoadingSpinner />
      )}

      {/* Mood Input - only show if no active workflow */}
      {!workflowState.sessionId && !workflowState.isLoading && (
        <div className="flex justify-center">
          <div className="w-full max-w-md">
            <MoodInput onSubmit={handleMoodSubmit} initialMood={selectedMood || undefined} />
          </div>
        </div>
      )}
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
      <div className="min-h-screen bg-background relative">
        {/* Fixed Dot Pattern Background */}
        <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
          <DotPattern
            className={cn(
              "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
            )}
          />
        </div>
        <div className="flex items-center justify-center min-h-screen">
          <AILoadingSpinner title="Loading..." subtitle="Setting up your experience" />
        </div>
      </div>
    }>
      <CreatePageWithAuth />
    </Suspense>
  );
}
