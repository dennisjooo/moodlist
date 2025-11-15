'use client';

import { Skeleton } from '@/components/ui/skeleton';
import { Music } from 'lucide-react';

interface TrackCardSkeletonProps {
    count?: number;
    className?: string;
}

/**
 * Skeleton loader for track cards during recommendation generation.
 * Shows animated placeholders to give the illusion of fast loading.
 */
export function TrackCardSkeleton({ count = 5, className = '' }: TrackCardSkeletonProps) {
    return (
        <div className={`space-y-2 ${className}`}>
            {Array.from({ length: count }).map((_, index) => (
                <div
                    key={index}
                    className="flex items-center gap-3 rounded-lg border border-border/50 bg-muted/20 p-3 animate-pulse"
                    style={{
                        animationDelay: `${index * 100}ms`,
                    }}
                >
                    {/* Album art skeleton */}
                    <div className="flex-shrink-0 w-12 h-12 rounded bg-muted/40 flex items-center justify-center">
                        <Music className="w-5 h-5 text-muted-foreground/30" />
                    </div>

                    {/* Track info skeleton */}
                    <div className="flex-1 space-y-2 min-w-0">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                    </div>

                    {/* Duration skeleton */}
                    <div className="flex-shrink-0">
                        <Skeleton className="h-3 w-10" />
                    </div>
                </div>
            ))}
        </div>
    );
}
