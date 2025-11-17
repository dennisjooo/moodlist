'use client';

import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Track } from '@/lib/types/workflow';
import { cn } from '@/lib/utils';
import { Music, Sparkles, Star } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface RealtimeTrackListProps {
  tracks: Track[];
  className?: string;
}

function TrackCard({
  track,
  index,
  isNew,
}: {
  track: Track;
  index: number;
  isNew: boolean;
}) {
  return (
    <div
      key={track.track_id}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border bg-card/60 backdrop-blur-sm',
        'transition-all duration-300',
        isNew && 'animate-in slide-in-from-left-5 fade-in duration-500'
      )}
    >
      {/* Track Number */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-sm font-semibold">
        {index + 1}
      </div>

      {/* Track Info */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
        <p className="text-xs text-muted-foreground truncate">
          {track.artists.join(', ')}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
            <span className="text-xs text-muted-foreground">
              {Math.round(track.confidence_score * 30 + 70)}%
            </span>
          </div>
          {track.source && (
            <Badge variant="outline" className="text-[10px] h-5 px-1.5">
              {track.source}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

export function RealtimeTrackList({
  tracks,
  className,
}: RealtimeTrackListProps) {
  const [previousCount, setPreviousCount] = useState(0);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  // Track when new tracks are added
  useEffect(() => {
    if (tracks.length > previousCount) {
      setPreviousCount(tracks.length);

      // Auto-scroll to bottom when new tracks arrive, but only if user hasn't scrolled up
      if (shouldAutoScroll.current && scrollAreaRef.current) {
        const scrollElement = scrollAreaRef.current.querySelector(
          '[data-radix-scroll-area-viewport]'
        );
        if (scrollElement) {
          setTimeout(() => {
            scrollElement.scrollTo({
              top: scrollElement.scrollHeight,
              behavior: 'smooth',
            });
          }, 100);
        }
      }
    }
  }, [tracks.length, previousCount]);

  // Detect manual scrolling to disable auto-scroll
  useEffect(() => {
    const scrollElement = scrollAreaRef.current?.querySelector(
      '[data-radix-scroll-area-viewport]'
    );
    if (!scrollElement) return;

    const handleScroll = () => {
      const isNearBottom =
        scrollElement.scrollHeight -
          scrollElement.scrollTop -
          scrollElement.clientHeight <
        100;
      shouldAutoScroll.current = isNearBottom;
    };

    scrollElement.addEventListener('scroll', handleScroll);
    return () => scrollElement.removeEventListener('scroll', handleScroll);
  }, []);

  if (tracks.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center py-12 text-center',
          className
        )}
      >
        <div className="rounded-full bg-primary/10 p-6 mb-4">
          <Music className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-lg font-semibold mb-2">Gathering tracks...</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Your personalized playlist is being crafted. Tracks will appear here
          as they&apos;re discovered.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold">
            Found {tracks.length} {tracks.length === 1 ? 'track' : 'tracks'}
          </h3>
        </div>
        <Badge variant="outline" className="text-xs">
          Live Updates
        </Badge>
      </div>

      <ScrollArea
        ref={scrollAreaRef}
        className="h-[500px] rounded-lg border bg-background/50 p-2"
      >
        <div className="space-y-2">
          {tracks.map((track, index) => (
            <TrackCard
              key={track.track_id}
              track={track}
              index={index}
              isNew={index >= previousCount - 1}
            />
          ))}
        </div>
      </ScrollArea>

      <div className="flex items-center justify-center text-xs text-muted-foreground gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Listening for new tracks...
      </div>
    </div>
  );
}
