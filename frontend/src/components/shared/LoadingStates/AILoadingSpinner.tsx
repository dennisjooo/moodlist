'use client';

import { Sparkles } from 'lucide-react';

interface AILoadingSpinnerProps {
  title?: string;
  subtitle?: string;
}

/**
 * Loading spinner with animated musical notes for AI playlist creation
 */
export default function AILoadingSpinner({
  title = 'Firing up the AI...',
  subtitle = 'Preparing to analyze your vibe',
}: AILoadingSpinnerProps) {
  return (
    <div className="relative flex min-h-[360px] flex-col items-center justify-center gap-10">
      <div className="relative h-32 w-32">
        {/* Ambient glow */}
        <div
          className="absolute inset-[-18%] rounded-full opacity-80 blur-3xl animate-[pulse_3s_ease-in-out_infinite]"
          style={{
            background:
              'radial-gradient(circle at center, hsl(var(--primary) / 0.35), hsl(var(--primary) / 0.05), transparent)',
          }}
        />

        {/* Subtle outer ring */}
        <div
          className="absolute inset-0 rounded-full border border-primary/30"
          style={{ background: 'hsl(var(--primary) / 0.06)' }}
        />

        {/* Gradient arc */}
        <div
          className="absolute inset-0 rounded-full opacity-80 animate-[spin_5s_linear_infinite]"
          style={{
            background:
              'conic-gradient(from 90deg, hsl(var(--primary) / 0.2) 0deg, hsl(var(--primary)) 140deg, transparent 320deg)',
          }}
        />

        {/* Inner halo */}
        <div
          className="absolute inset-[18%] rounded-full border border-primary/40 bg-background/80 backdrop-blur"
          style={{ boxShadow: '0 0 40px -15px hsl(var(--primary) / 0.6)' }}
        />

        {/* Orbiting accents */}
        <div className="absolute inset-[4%] animate-[spin_8s_linear_infinite]">
          <div
            className="absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 rounded-full bg-primary"
            style={{ boxShadow: '0 0 20px 4px hsl(var(--primary) / 0.4)' }}
          />
          <div
            className="absolute right-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-primary/60"
            style={{ boxShadow: '0 0 20px 2px hsl(var(--primary) / 0.3)' }}
          />
          <div
            className="absolute left-[12%] bottom-[10%] h-2.5 w-2.5 rounded-full bg-primary/40"
            style={{ boxShadow: '0 0 18px 3px hsl(var(--primary) / 0.25)' }}
          />
        </div>

        {/* Central icon */}
        <div className="absolute inset-[30%] flex items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-8 w-8 text-primary animate-[pulse_2.6s_ease-in-out_infinite]" />
        </div>
      </div>

      <div className="space-y-3 text-center">
        <p className="text-lg font-semibold tracking-tight text-foreground">
          {title}
        </p>
        <p className="text-sm text-muted-foreground">
          {subtitle}
        </p>
      </div>
    </div>
  );
}

