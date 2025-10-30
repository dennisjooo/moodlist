'use client';

import { ReactNode } from 'react';
import Navigation from '@/components/Navigation';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';

interface CreatePageLayoutProps {
  children: ReactNode;
}

/**
 * Shared layout for create page views
 * Includes background pattern and navigation
 */
export function CreatePageLayout({ children }: CreatePageLayoutProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/90 to-background">
      {/* Ambient gradients */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div
          aria-hidden="true"
          className="absolute left-[-20%] top-[-20%] h-[40rem] w-[40rem] rounded-full bg-primary/30 blur-[140px] opacity-60"
        />
        <div
          aria-hidden="true"
          className="absolute right-[-15%] bottom-[-25%] h-[36rem] w-[36rem] rounded-full bg-muted/40 blur-[160px] opacity-60"
        />
      </div>

      {/* Subtle dot pattern overlay */}
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(420px_circle_at_center,white,transparent)]",
            "text-muted-foreground/10"
          )}
        />
      </div>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-4xl items-center px-4 py-16 sm:px-6 lg:px-8">
        <div className="w-full rounded-3xl border border-border/40 bg-background/70 p-6 shadow-[0_30px_70px_-35px_rgba(15,23,42,0.35)] backdrop-blur-xl sm:p-10">
          {children}
        </div>
      </main>
    </div>
  );
}

