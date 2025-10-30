'use client';

import { AuthGuard } from '@/components/AuthGuard';
import Navigation from '@/components/Navigation';
import { PlaylistsPageContent } from '@/components/features/playlist/PlaylistsPage';
import { PlaylistGridSkeleton } from '@/components/shared/LoadingStates';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import { Suspense } from 'react';

export default function PlaylistsPage() {
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
        <Navigation />
        <main className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <PlaylistGridSkeleton />
        </main>
      </div>
    }>
      <AuthGuard optimistic={true}>
        <PlaylistsPageContent />
      </AuthGuard>
    </Suspense>
  );
}