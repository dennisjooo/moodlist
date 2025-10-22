'use client';

import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/lib/hooks/useReducedMotion';
import { cn } from '@/lib/utils';
import { ExternalLink, Star } from 'lucide-react';
import { memo } from 'react';

interface Track {
  track_id: string;
  track_name: string;
  artists: string[];
  confidence_score: number;
  spotify_uri?: string;
}

interface TrackRowProps {
  track: Track;
  index: number;
  isFocused?: boolean;
}

function TrackRow({ track, index, isFocused }: TrackRowProps) {
  const prefersReducedMotion = useReducedMotion();

  const getSpotifyUrl = (uri?: string) => {
    if (!uri) return null;
    if (uri.startsWith('http')) return uri;
    if (uri.startsWith('spotify:track:')) {
      return `https://open.spotify.com/track/${uri.split(':')[2]}`;
    }
    return `https://open.spotify.com/track/${uri}`;
  };

  const spotifyUrl = getSpotifyUrl(track.spotify_uri);

  return (
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

        {spotifyUrl && (
          <Button
            size="sm"
            variant="ghost"
            className={cn(
              "h-7 w-7 p-0",
              isFocused ? "opacity-100" : "opacity-0 group-hover:opacity-100",
              prefersReducedMotion ? "transition-none" : "transition-opacity"
            )}
            asChild
            aria-label={`Open ${track.track_name} in Spotify`}
          >
            <a
              href={spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </a>
          </Button>
        )}
      </div>
    </div>
  );
}

export default memo(TrackRow);

