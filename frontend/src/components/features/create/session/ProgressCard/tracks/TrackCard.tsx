'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Track } from '@/lib/types/workflow';
import { Star } from 'lucide-react';

interface TrackCardProps {
    track: Track;
    index: number;
    isNew: boolean;
}

export function TrackCard({ track, index, isNew }: TrackCardProps) {
    return (
        <div
            className={cn(
                'flex items-center gap-3 p-3 rounded-lg border border-border/40',
                'bg-gradient-to-br from-card via-card/95 to-card/90',
                'transition-all duration-300 hover:shadow-sm hover:border-border/60',
                isNew && 'animate-in slide-in-from-top-2 fade-in duration-500'
            )}
        >
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 via-primary/15 to-primary/10 flex items-center justify-center text-sm font-semibold">
                {index + 1}
            </div>

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
                        <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-border/40">
                            {track.source}
                        </Badge>
                    )}
                </div>
            </div>
        </div>
    );
}
