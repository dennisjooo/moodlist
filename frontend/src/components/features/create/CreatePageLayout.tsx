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
    <div className="relative h-screen overflow-hidden flex flex-col">

      {/* Subtle dot pattern overlay */}
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
          )}
        />
      </div>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10 mx-auto flex flex-1 w-full max-w-4xl items-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="w-full">
          {children}
        </div>
      </main>
    </div>
  );
}

