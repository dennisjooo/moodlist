'use client';

import { Badge } from '@/components/ui/badge';
import { Sparkles } from 'lucide-react';

/**
 * Header section for the create page
 * Shows title and description for mood input
 */
export function CreatePageHeader() {
  return (
    <div className="mb-6 text-center">
      <Badge
        variant="outline"
        className="mx-auto mb-3 flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-4 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur"
        aria-label="Feature badge"
      >
        <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
        Curated by AI
      </Badge>

      <div className="space-y-2">
        <h1 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          Craft the soundtrack to your moment
        </h1>
        <p className="mx-auto max-w-2xl text-sm text-muted-foreground sm:text-base">
          Share the vibe you&apos;re chasing and our AI blends it into a bespoke Spotify playlist—complete with tracks that match your energy.
        </p>
      </div>
    </div>
  );
}

