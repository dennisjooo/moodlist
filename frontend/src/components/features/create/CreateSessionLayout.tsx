'use client';

import { ReactNode } from 'react';
import Navigation from '@/components/Navigation';
import MoodBackground from '@/components/shared/MoodBackground';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';

interface ColorScheme {
  primary: string;
  secondary: string;
  tertiary: string;
}

interface CreateSessionLayoutProps {
  children: ReactNode;
  colorScheme?: ColorScheme;
  dimmed?: boolean;
}

export const createSessionCardClassName =
  'rounded-3xl border border-border/40 bg-background/80 p-6 sm:p-8 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl';

export function CreateSessionLayout({
  children,
  colorScheme,
  dimmed = false,
}: CreateSessionLayoutProps) {
  return (
    <div
      className={cn(
        'relative min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-background',
        'flex flex-col transition-opacity duration-300 ease-in-out',
        dimmed && 'pointer-events-none opacity-60'
      )}
    >
      <MoodBackground colorScheme={colorScheme} style="linear-diagonal" opacity={0.18} />

      <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            '[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]'
          )}
        />
      </div>

      <Navigation />

      <main className="relative z-10 mx-auto flex w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex w-full flex-col justify-center space-y-6">{children}</div>
      </main>
    </div>
  );
}

