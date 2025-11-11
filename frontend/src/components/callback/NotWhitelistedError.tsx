'use client';

import { AlertTriangle, ExternalLink, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { config } from '@/lib/config';

interface NotWhitelistedErrorProps {
  errorMessage: string;
  onRetry: () => void;
}

export function NotWhitelistedError({ errorMessage, onRetry }: NotWhitelistedErrorProps) {
  const { betaContactUrl, betaContactLabel } = config.access;

  return (
    <div className="space-y-6 pb-8">
      {/* Error Icon */}
      <div className="flex justify-center">
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <span className="absolute inset-0 rounded-full border-2 border-destructive/30" />
          <AlertTriangle className="h-8 w-8 text-destructive" />
        </div>
      </div>

      {/* Error Message */}
      <div className="space-y-3 text-center">
        <h3 className="text-xl font-semibold text-foreground">
          Not Whitelisted
        </h3>
      </div>

      {/* Info Box */}
      <div className="rounded-lg border border-border/60 bg-muted/30 p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 flex-shrink-0 mt-0.5">
            <span className="text-xs font-bold text-primary">!</span>
          </div>
          <div className="space-y-2 text-sm">
            <p className="font-medium text-foreground">
              Why is this happening?
            </p>
            <p className="text-muted-foreground leading-relaxed">
              MoodList is currently using Spotify&apos;s Development Mode API, which limits access to 25 manually whitelisted users. This is a Spotify restriction, not ours.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              In the meantime, we&apos;re accepting a limited number of beta testers.
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-3 pt-2">
        {betaContactUrl && (
          <Button
            asChild
            size="lg"
            className="w-full"
          >
            <a
              href={betaContactUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2"
            >
              {betaContactLabel || 'Request Beta Access'}
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        )}

        <Button
          variant="outline"
          size="lg"
          onClick={onRetry}
          className="w-full flex items-center justify-center gap-2"
        >
          <Home className="h-4 w-4" />
          Return to Homepage
        </Button>
      </div>

      {/* Additional Help */}
      <div className="text-center pt-2">
        <p className="text-xs text-muted-foreground">
          Already whitelisted?{' '}
          <button
            onClick={onRetry}
            className="text-primary hover:underline font-medium"
          >
            Try logging in again
          </button>
        </p>
      </div>
    </div>
  );
}
