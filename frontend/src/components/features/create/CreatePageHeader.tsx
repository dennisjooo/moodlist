'use client';

import { Badge } from '@/components/ui/badge';
import { Sparkles } from 'lucide-react';

/**
 * Header section for the create page
 * Shows title and description for mood input
 */
export function CreatePageHeader() {
  return (
    <div className="text-center mb-12">
      <Badge 
        variant="outline" 
        className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6"
        aria-label="Feature badge"
      >
        <Sparkles className="w-4 h-4" aria-hidden="true" />
        AI-Powered Playlist Creation
      </Badge>

      <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
        What&apos;s your mood?
      </h1>
      <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
        Describe how you&apos;re feeling and our AI will create the perfect Spotify playlist for your moment.
      </p>
    </div>
  );
}

