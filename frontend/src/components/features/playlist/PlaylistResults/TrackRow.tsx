'use client';

import { TooltipProvider } from '@/components/ui/tooltip';
import { useReducedMotion } from '@/lib/hooks';
import { Track } from '@/lib/types/track';
import { cn } from '@/lib/utils';
import { Star } from 'lucide-react';
import { memo } from 'react';
import TrackDetailsTooltip from '../TrackDetailsTooltip';

interface TrackRowProps {
  track: Track;
  index: number;
  isFocused?: boolean;
}

function TrackRow({ track, index, isFocused }: TrackRowProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <TooltipProvider>
      <div
        className={cn(
          "flex items-center gap-3 p-2.5 rounded-lg group cursor-pointer",
          isFocused && "bg-accent ring-2 ring-ring ring-offset-2",
          !isFocused && "hover:bg-accent/50",
          prefersReducedMotion ? "transition-none" : "transition-colors"
        )}
        role="option"
        aria-label={`Track ${index + 1}: ${track.track_name} by ${track.artists.join(', ')}`}
        aria-selected={isFocused}
        tabIndex={-1}
      >
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
          {index + 1}
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
          <p className="text-xs text-muted-foreground truncate">
            {track.artists.join(', ')}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" aria-hidden="true" />
            <span className="text-xs text-muted-foreground">
              {Math.round(track.confidence_score * 30 + 70)}%
            </span>
          </div>

          {track.spotify_uri && <TrackDetailsTooltip spotifyUri={track.spotify_uri} />}
        </div>
      </div>
    </TooltipProvider>
  );
}

export default memo(TrackRow);

