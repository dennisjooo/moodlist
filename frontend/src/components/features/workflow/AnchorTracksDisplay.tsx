'use client';

import { Badge } from '@/components/ui/badge';
import type { AnchorTrack } from '@/types/workflow';

interface AnchorTracksDisplayProps {
    anchorTracks: AnchorTrack[];
}

export function AnchorTracksDisplay({ anchorTracks }: AnchorTracksDisplayProps) {
    if (anchorTracks.length === 0) {
        return null;
    }

    return (
        <div className="rounded-lg border border-border/60 bg-gradient-to-br from-muted/30 via-muted/20 to-muted/10 p-4 space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.2em] text-foreground/80 font-semibold">
                    Foundation Tracks
                </p>
                <Badge
                    variant="outline"
                    className="text-[10px] px-2 py-0.5 border-border/50 bg-muted/50 font-medium"
                >
                    Anchor
                </Badge>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
                Hand-picked songs we&apos;re using as the blueprint for your vibe
            </p>
            <div className="space-y-2.5">
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
        </div>
    );
}
