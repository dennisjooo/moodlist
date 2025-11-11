'use client';

import { AlertTriangle, ExternalLink, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { config } from '@/lib/config';

interface NotWhitelistedErrorProps {
  errorMessage: string;
  onRetry: () => void;
}

export function NotWhitelistedError({ errorMessage, onRetry }: NotWhitelistedErrorProps) {
  const { betaContactUrl, betaContactLabel } = config.access;

  return (
    <div className="space-y-6 pb-8">
      {/* Beta Registration CTA */}
      {betaContactUrl && (
        <div className="rounded-lg border border-primary/30 bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5 p-5 space-y-4">
          <div className="text-center space-y-2">
            <FeatureBadge>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              Limited Spots Available
            </FeatureBadge>
            <h4 className="text-lg font-semibold text-foreground">
              Join the Beta Waitlist
            </h4>
            <p className="text-sm text-muted-foreground">
              MoodList is currently using Spotify&apos;s Development Mode API, which limits access to 25 manually whitelisted users.
            </p>
            <p className="text-sm font-bold text-muted-foreground">
             This is a Spotify restriction, not ours.
            </p>
          </div>

          <Button
            asChild
            size="lg"
            className="w-full shadow-lg hover:shadow-xl transition-shadow"
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
        </div>
      )}

      {/* Secondary Action */}
      <div className="flex flex-col gap-3">{!betaContactUrl && (
        <div className="rounded-lg border border-primary/30 bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5 p-5 space-y-4">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-semibold">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              Limited Spots Available
            </div>
            <h4 className="text-lg font-semibold text-foreground">
              Join the Beta Waitlist
            </h4>
            <p className="text-sm text-muted-foreground">
              Be among the first to experience MoodList when we expand access. We&apos;ll notify you as soon as a spot opens up!
            </p>
          </div>

          <Button
            asChild
            size="lg"
            className="w-full shadow-lg hover:shadow-xl transition-shadow"
          >
            <a
              href={`mailto:${config.access.betaContactUrl || 'hello@moodlist.app'}?subject=Beta Access Request`}
              className="flex items-center justify-center gap-2"
            >
              Request Beta Access
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        </div>
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
