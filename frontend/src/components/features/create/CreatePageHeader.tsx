'use client';

import { FeatureBadge } from '@/components/ui/feature-badge';
import { Sparkles } from 'lucide-react';

/**
 * Header section for the create page
 * Shows title and description for mood input
 */
export function CreatePageHeader() {
  return (
    <div className="mb-6 text-center">
      <FeatureBadge icon={Sparkles} className="mb-3" ariaLabel="Feature badge">
        Curated by AI
      </FeatureBadge>

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

