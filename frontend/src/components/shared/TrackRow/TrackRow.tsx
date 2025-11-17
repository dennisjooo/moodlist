'use client';

import { Badge } from '@/components/ui/badge';
import { TooltipProvider } from '@/components/ui/tooltip';
import { motion } from '@/components/ui/lazy-motion';
import { TRACK_ROW_SLIDE_IN_VARIANTS } from '@/lib/constants/animations';
import { useReducedMotion } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { Star } from 'lucide-react';
import { memo } from 'react';
import TrackDetailsTooltip from '@/components/features/playlist/TrackDetailsTooltip';
import type { AnchorTrack } from '@/lib/types/workflow';

// Support both Track types (from track.ts and workflow.ts)
interface BaseTrack {
  track_id: string;
  track_name: string;
  artists: string[];
  confidence_score: number;
  spotify_uri?: string;
}

interface WorkflowTrack extends BaseTrack {
  source?: string;
  reasoning?: string;
}

type Track = BaseTrack | WorkflowTrack | AnchorTrack;

// Helper function to get track name from different track types
function getTrackName(track: Track): string {
  if ('name' in track) {
    return track.name;
  }
  return track.track_name;
}

// Helper function to get confidence score from different track types
function getConfidenceScore(track: Track): number {
  if ('confidence_score' in track) {
    return track.confidence_score;
  }
  return 0.8; // Default confidence for anchor tracks
}

// Helper function to get spotify URI from different track types
function getSpotifyUri(track: Track): string | undefined {
  if ('spotify_uri' in track) {
    return track.spotify_uri;
  }
  return undefined;
}

interface BadgeConfig {
  label: string;
  variant?: 'default' | 'secondary' | 'outline' | 'destructive';
  className?: string;
}

interface TrackRowProps {
  track: Track;
  index: number;
  isFocused?: boolean;
  isNew?: boolean;
  showSource?: boolean;
  badge?: BadgeConfig;
  showRating?: boolean;
}

function TrackRow({ track, index, isFocused, isNew, showSource, badge, showRating = true }: TrackRowProps) {
  const prefersReducedMotion = useReducedMotion();
  const workflowTrack = track as WorkflowTrack;

  return (
    <TooltipProvider>
      <motion.div
        className={cn(
          "flex items-center gap-3 p-2.5 rounded-lg group cursor-pointer",
          isFocused && "bg-accent ring-2 ring-ring ring-offset-2",
          !isFocused && "hover:bg-accent/50",
          prefersReducedMotion ? "transition-none" : "transition-colors",
          isNew && !prefersReducedMotion && "animate-in slide-in-from-top-2 fade-in duration-500"
        )}
        role="option"
        aria-label={`Track ${index + 1}: ${getTrackName(track)} by ${track.artists.join(', ')}`}
        aria-selected={isFocused}
        tabIndex={-1}
        variants={TRACK_ROW_SLIDE_IN_VARIANTS}
        initial="hidden"
        animate="visible"
      >
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
          {index + 1}
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm truncate">{getTrackName(track)}</h4>
          <p className="text-xs text-muted-foreground truncate">
            {track.artists.join(', ')}
          </p>
          {showSource && workflowTrack.source && (
            <div className="mt-1">
              <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-border/40">
                {workflowTrack.source.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </Badge>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {badge && (
            <Badge variant={badge.variant || 'outline'} className={badge.className}>
              {badge.label}
            </Badge>
          )}

          {showRating && (
            <div className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" aria-hidden="true" />
              <span className="text-xs text-muted-foreground">
                {Math.round(getConfidenceScore(track) * 30 + 70)}%
              </span>
            </div>
          )}

          {getSpotifyUri(track) && <TrackDetailsTooltip spotifyUri={getSpotifyUri(track)!} />}
        </div>
      </motion.div>
    </TooltipProvider>
  );
}

export default memo(TrackRow);
