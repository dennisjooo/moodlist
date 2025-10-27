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
      <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center min-h-[calc(100vh-4rem)]">
        <div className="w-full">
          {children}
        </div>
      </main>
    </div>
  );
}

