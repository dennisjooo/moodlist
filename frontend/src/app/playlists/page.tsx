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
    <Suspense
      fallback={
        <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-background">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-[-18%] top-[-18%] h-[32rem] w-[32rem] -z-20 rounded-full bg-primary/25 blur-[130px] opacity-70"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute right-[-20%] bottom-[-25%] h-[30rem] w-[30rem] -z-20 rounded-full bg-muted/40 blur-[150px] opacity-70"
          />
          <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
            <DotPattern
              className={cn(
                "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                "text-muted-foreground/10",
              )}
            />
          </div>
          <div className="relative z-20">
            <Navigation />
          </div>
          <main className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-20 pt-28 sm:px-6 lg:px-8">
            <section className="rounded-3xl border border-border/40 bg-background/80 p-8 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
              <PlaylistGridSkeleton />
            </section>
          </main>
        </div>
      }
    >
      <AuthGuard optimistic={true}>
        <PlaylistsPageContent />
      </AuthGuard>
    </Suspense>
  );
}