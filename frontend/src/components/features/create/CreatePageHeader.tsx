'use client';

import { Badge } from '@/components/ui/badge';
import { Sparkles } from 'lucide-react';

/**
 * Header section for the create page
 * Shows title and description for mood input
 */
export function CreatePageHeader() {
  return (
    <div className="mb-10 text-center">
      <Badge
        variant="outline"
        className="mx-auto mb-5 flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-5 py-1.5 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur"
        aria-label="Feature badge"
      >
        <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
        Curated by AI
      </Badge>

      <div className="space-y-4">
        <h1 className="mx-auto max-w-2xl text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          Craft the soundtrack to your moment
        </h1>
        <p className="mx-auto max-w-2xl text-base text-muted-foreground sm:text-lg">
          Share the vibe you&apos;re chasing and our AI blends it into a bespoke Spotify playlist—complete with tracks that match your energy.
        </p>
      </div>
    </div>
  );
}

