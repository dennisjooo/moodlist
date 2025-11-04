'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/lib/hooks';
import type { Track } from '@/lib/types/workflow';
import { cn } from '@/lib/utils';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Loader2, Star, Trash2 } from 'lucide-react';
import { memo } from 'react';
import TrackDetailsTooltip from '../TrackDetailsTooltip';

export interface TrackItemProps {
    track: Track;
    index: number;
    onRemove: (trackId: string) => void;
    isRemoving: boolean;
}

export const TrackItem = memo(function TrackItem({ track, index, onRemove, isRemoving }: TrackItemProps) {
    const prefersReducedMotion = useReducedMotion();

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: track.track_id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition: prefersReducedMotion ? 'none' : transition,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "flex items-center gap-4 p-4 rounded-lg border-2 bg-card group",
                prefersReducedMotion ? "transition-none" : "transition-all duration-200",
                isDragging && "shadow-2xl scale-105 z-50 bg-accent border-primary/50 ring-2 ring-primary/20",
                !isDragging && "hover:bg-accent/50 hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5"
            )}
        >
            {/* Drag Handle */}
            <div
                {...attributes}
                {...listeners}
                className="flex-shrink-0 cursor-grab active:cursor-grabbing touch-none"
                style={{ touchAction: 'none' }}
            >
                <GripVertical className="w-5 h-5 text-muted-foreground group-hover:text-foreground group-hover:scale-110 transition-all" />
            </div>

            {/* Track Number */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 group-hover:from-primary/30 group-hover:to-primary/20 flex items-center justify-center text-sm font-semibold transition-all">
                {index + 1}
            </div>

            {/* Track Info */}
            <div className="flex-1 min-w-0">
                <h4 className="font-medium truncate">{track.track_name}</h4>
                <p className="text-sm text-muted-foreground truncate">
                    {track.artists.join(', ')}
                </p>
                <div className="flex items-center gap-2 mt-1">
                    <div className="flex items-center gap-1">
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <span className="text-xs text-muted-foreground">
                            {Math.round(track.confidence_score * 30 + 70)}%
                        </span>
                    </div>
                    <Badge variant="outline" className="text-xs capitalize">
                        {track.source.replace(/_/g, ' ')}
                    </Badge>
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 flex-shrink-0">
                {track.spotify_uri && <TrackDetailsTooltip spotifyUri={track.spotify_uri} />}

                <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onRemove(track.track_id)}
                    disabled={isRemoving}
                    className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                >
                    {isRemoving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Trash2 className="w-4 h-4" />
                    )}
                </Button>
            </div>
        </div>
    );
});

