'use client';

import { ReactNode } from 'react';
import Navigation from '@/components/Navigation';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';

interface ProfilePageLayoutProps {
  children: ReactNode;
}

export function ProfilePageLayout({ children }: ProfilePageLayoutProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-background">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div
          aria-hidden="true"
          className="absolute left-[-18%] top-[-18%] h-[30rem] w-[30rem] rounded-full bg-primary/25 blur-[120px] opacity-70"
        />
        <div
          aria-hidden="true"
          className="absolute right-[-20%] bottom-[-25%] h-[28rem] w-[28rem] rounded-full bg-muted/40 blur-[140px] opacity-60"
        />
      </div>

      <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            '[mask-image:radial-gradient(520px_circle_at_center,white,transparent)]',
            'text-muted-foreground/10'
          )}
        />
      </div>

      <Navigation />

      <main className="relative z-10 flex min-h-[calc(100vh-4rem)] w-full flex-col">
        <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-8 sm:px-6 lg:px-8 min-h-0">
          {children}
        </div>
      </main>
    </div>
  );
}

