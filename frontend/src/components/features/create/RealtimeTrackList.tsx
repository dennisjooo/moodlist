'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
        'flex items-center gap-3 p-3 rounded-lg border border-border/40',
        'bg-gradient-to-br from-card via-card/95 to-card/90',
        'transition-all duration-300 hover:shadow-sm hover:border-border/60',
        isNew && 'animate-in slide-in-from-top-2 fade-in duration-500'
      )}
    >
      {/* Track Number */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 flex items-center justify-center text-sm font-semibold">
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

  return (
    <Card
      className={cn(
        'w-full overflow-hidden transition-all duration-300',
        'border-border/60 shadow-sm hover:shadow-md',
        'bg-gradient-to-br from-card via-card to-card/95',
        className
      )}
    >
      <CardHeader className="pb-3 border-b border-border/40 bg-gradient-to-r from-muted/20 to-transparent">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base flex items-center gap-2.5 font-semibold">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="bg-gradient-to-br from-foreground to-foreground/80 bg-clip-text">
              Live Tracks
            </span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs border-border/40">
              {tracks.length} {tracks.length === 1 ? 'track' : 'tracks'}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {tracks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center px-4">
            <div className="rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 p-6 mb-4">
              <Music className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-base font-semibold mb-2">Gathering tracks...</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Your personalized playlist is being crafted. Tracks will appear here
              as they&apos;re discovered.
            </p>
          </div>
        ) : (
          <>
            <ScrollArea
              ref={scrollAreaRef}
              className="h-[calc(100vh-28rem)] lg:h-[600px]"
            >
              <div className="space-y-2 p-4">
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

            <div className="flex items-center justify-center text-xs text-muted-foreground gap-2 py-3 border-t border-border/40 bg-gradient-to-r from-muted/20 to-transparent">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              Listening for new tracks...
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
