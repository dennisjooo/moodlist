'use client';

import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { AnchorTrack, Track } from '@/lib/types/workflow';
import { Music, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { TrackCard } from './TrackCard';

interface TracksPanelProps {
    tracks: Track[];
    showAnchors: boolean;
    anchorTracks?: AnchorTrack[];
}

export function TracksPanel({ tracks, showAnchors, anchorTracks }: TracksPanelProps) {
    const [previousCount, setPreviousCount] = useState(0);
    const scrollAreaRef = useRef<HTMLDivElement>(null);
    const shouldAutoScroll = useRef(true);

    useEffect(() => {
        if (tracks.length > previousCount) {
            setPreviousCount(tracks.length);

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

    const showTracks = tracks.length > 0;

    if (showAnchors && anchorTracks?.length) {
        return (
            <div className="flex flex-col h-full">
                <div className="flex items-center justify-between gap-3 px-1 pb-3">
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <h3 className="text-sm font-semibold">Foundation Tracks</h3>
                    </div>
                    <Badge variant="outline" className="text-xs border-border/40">
                        {anchorTracks.length} {anchorTracks.length === 1 ? 'track' : 'tracks'}
                    </Badge>
                </div>

                <ScrollArea className="h-[400px]">
                    <div className="space-y-2 p-2 pr-4">
                        {anchorTracks.map((track, index) => (
                            <div
                                key={`${track.id}-${index}`}
                                className="group flex items-center gap-3 rounded-lg border border-border/40 bg-gradient-to-r from-muted/40 to-muted/20 hover:from-muted/50 hover:to-muted/30 px-3.5 py-2.5 animate-in fade-in duration-300 transition-all hover:shadow-sm hover:border-border/60"
                                style={{ animationDelay: `${index * 80}ms` }}
                            >
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-semibold text-foreground truncate transition-colors">
                                        {track.name}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                        {track.artists.join(', ')}
                                    </p>
                                    {track.albumName && (
                                        <p className="text-[10px] text-muted-foreground/70 truncate mt-0.5">
                                            {track.albumName}
                                        </p>
                                    )}
                                </div>
                                <div className="flex flex-col items-end gap-1.5 shrink-0">
                                    {track.user_mentioned && (
                                        <Badge variant="secondary" className="text-[10px] px-2 py-0.5 bg-primary/10 border-primary/20 font-medium">
                                            Your pick
                                        </Badge>
                                    )}
                                    {track.anchor_type === 'genre' && !track.user_mentioned && (
                                        <Badge variant="outline" className="text-[10px] px-2 py-0.5 border-border/50 bg-muted/50 font-medium">
                                            Genre fit
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </ScrollArea>

                <div className="flex items-center justify-center text-xs text-muted-foreground gap-2 pt-3">
                    Tracks we&apos;re using to create as the foundation for your playlist.
                </div>
            </div>
        );
    }

    if (!showTracks) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center px-4">
                <div className="rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 p-6 mb-4">
                    <Music className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-base font-semibold mb-2">Gathering tracks...</h3>
                <p className="text-sm text-muted-foreground max-w-sm">
                    Your personalized playlist is being crafted.<br/>Tracks will appear here
                    as they&apos;re discovered.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between gap-3 px-1 pb-3">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <h3 className="text-sm font-semibold">Live Tracks</h3>
                </div>
                <Badge variant="outline" className="text-xs border-border/40">
                    {tracks.length} {tracks.length === 1 ? 'track' : 'tracks'}
                </Badge>
            </div>

            <ScrollArea
                ref={scrollAreaRef}
                className="h-[400px]"
            >
                <div className="space-y-2 p-2 pr-4">
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

            <div className="flex items-center justify-center text-xs text-muted-foreground gap-2 pt-3">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                Listening for new tracks...
            </div>
        </div>
    );
}
