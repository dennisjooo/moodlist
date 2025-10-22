'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { spotifyAPI, TrackDetails } from '@/lib/api/spotify';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { AlertCircle, Calendar, Clock, Disc, Hash, Info, Music, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';

interface TrackDetailsTooltipProps {
    trackId: string;
    className?: string;
}

export default function TrackDetailsTooltip({ trackId, className }: TrackDetailsTooltipProps) {
    const [trackDetails, setTrackDetails] = useState<TrackDetails | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);

    const handleOpenChange = async (open: boolean) => {
        if (open && !hasLoaded) {
            setIsLoading(true);
            setError(null);
            try {
                const details = await spotifyAPI.getTrackDetails(trackId);
                logger.debug('Track details loaded', { component: 'TrackDetailsTooltip', trackId, details });
                setTrackDetails(details);
                setHasLoaded(true);
            } catch (err) {
                logger.error('Failed to fetch track details', err, { component: 'TrackDetailsTooltip', trackId });
                setError('Failed to load track details');
            } finally {
                setIsLoading(false);
            }
        }
    };

    const formatDuration = (ms: number) => {
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    const formatReleaseDate = (dateString: string) => {
        if (!dateString) return 'Unknown';
        const parts = dateString.split('-');
        if (parts.length === 1) return parts[0]; // Year only
        if (parts.length === 2) return `${parts[1]}/${parts[0]}`; // Month/Year
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    return (
        <Tooltip onOpenChange={handleOpenChange} delayDuration={200}>
            <TooltipTrigger asChild>
                <button
                    className={cn(
                        'inline-flex items-center justify-center rounded-full hover:bg-accent p-1 transition-colors',
                        className
                    )}
                    aria-label="View track details"
                >
                    <Info className="w-4 h-4 text-muted-foreground" />
                </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="w-[360px] p-0 overflow-hidden" sideOffset={8}>
                {isLoading && (
                    <div className="space-y-3 p-4">
                        {/* Header skeleton */}
                        <div className="space-y-0.5">
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-3 w-1/2" />
                        </div>

                        {/* Divider */}
                        <div className="border-t border-border/50" />

                        {/* Content skeleton */}
                        <div className="flex items-start gap-4">
                            {/* Left side - Details skeleton */}
                            <div className="flex-1 min-w-0 space-y-2">
                                <Skeleton className="h-3 w-full" />
                                <Skeleton className="h-3 w-2/3" />
                                <Skeleton className="h-3 w-1/2" />
                                <Skeleton className="h-3 w-3/4" />
                                <Skeleton className="h-3 w-1/3" />
                            </div>

                            {/* Right side - Album cover skeleton */}
                            <Skeleton className="w-28 h-28 rounded-md flex-shrink-0" />
                        </div>
                    </div>
                )}
                {error && (
                    <div className="p-4 text-sm text-destructive">
                        {error}
                    </div>
                )}
                {trackDetails && !isLoading && !error && (
                    <div className="space-y-3 p-4">
                        {/* Header - Track name and artist */}
                        <div className="space-y-0.5">
                            <h4 className="font-semibold text-sm leading-tight truncate">
                                {trackDetails.track_name}
                            </h4>
                            <p className="text-xs text-muted-foreground truncate">
                                {trackDetails.artists.map(a => a.name).join(', ')}
                            </p>
                        </div>

                        {/* Divider */}
                        <div className="border-t border-border/50" />

                        {/* Content - Details and Cover side by side */}
                        <div className="flex items-start gap-4">
                            {/* Left side - Details with icons */}
                            <div className="flex-1 min-w-0 space-y-2 text-xs text-foreground/80">
                                {trackDetails.album?.name && (
                                    <div className="flex items-start gap-2.5">
                                        <Disc className="w-3.5 h-3.5 text-muted-foreground/70 flex-shrink-0 mt-0.5" />
                                        <span className="truncate leading-relaxed">{trackDetails.album.name}</span>
                                    </div>
                                )}

                                {trackDetails.duration_ms && (
                                    <div className="flex items-center gap-2.5">
                                        <Clock className="w-3.5 h-3.5 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-relaxed">{formatDuration(trackDetails.duration_ms)}</span>
                                    </div>
                                )}

                                {trackDetails.album?.release_date && (
                                    <div className="flex items-center gap-2.5">
                                        <Calendar className="w-3.5 h-3.5 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-relaxed">{formatReleaseDate(trackDetails.album.release_date)}</span>
                                    </div>
                                )}

                                {trackDetails.track_number && trackDetails.album?.total_tracks && (
                                    <div className="flex items-center gap-2.5">
                                        <Hash className="w-3.5 h-3.5 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-relaxed">Track {trackDetails.track_number} of {trackDetails.album.total_tracks}</span>
                                    </div>
                                )}

                                {trackDetails.popularity !== undefined && trackDetails.popularity > 0 && (
                                    <div className="flex items-center gap-2.5">
                                        <TrendingUp className="w-3.5 h-3.5 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-relaxed">{trackDetails.popularity}/100</span>
                                    </div>
                                )}

                                {trackDetails.explicit && (
                                    <div className="flex items-center gap-2.5">
                                        <AlertCircle className="w-3.5 h-3.5 text-destructive/80 flex-shrink-0" />
                                        <span className="text-destructive/90 leading-relaxed">Explicit</span>
                                    </div>
                                )}
                            </div>

                            {/* Right side - Album Cover */}
                            {trackDetails.album_image ? (
                                <div className="w-28 h-28 rounded-md overflow-hidden bg-muted flex-shrink-0 shadow-md">
                                    <Image
                                        src={trackDetails.album_image}
                                        alt={trackDetails.album.name}
                                        width={112}
                                        height={112}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            ) : (
                                <div className="w-28 h-28 rounded-md bg-muted flex items-center justify-center flex-shrink-0 shadow-md">
                                    <Music className="w-10 h-10 text-muted-foreground/40" />
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </TooltipContent>
        </Tooltip>
    );
}

