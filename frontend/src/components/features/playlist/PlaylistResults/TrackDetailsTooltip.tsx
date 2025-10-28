'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { spotifyAPI, TrackDetails } from '@/lib/api/spotify';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { AlertCircle, Calendar, Clock, Disc, Hash, Info, Music, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';

interface TrackDetailsTooltipProps {
    spotifyUri: string;
    className?: string;
}

export default function TrackDetailsTooltip({ spotifyUri, className }: TrackDetailsTooltipProps) {
    const [trackDetails, setTrackDetails] = useState<TrackDetails | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    const handleOpenChange = async (open: boolean) => {
        setIsOpen(open);

        if (open && !hasLoaded) {
            setIsLoading(true);
            setError(null);
            try {
                const details = await spotifyAPI.getTrackDetails(spotifyUri);
                logger.debug('Track details loaded', { component: 'TrackDetailsTooltip', spotifyUri, details });
                setTrackDetails(details);
                setHasLoaded(true);
            } catch (err) {
                logger.error('Failed to fetch track details', err, { component: 'TrackDetailsTooltip', spotifyUri });
                setError('Failed to load track details');
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handleClick = (e: React.MouseEvent) => {
        // Prevent the default tooltip behavior to avoid flicker
        e.preventDefault();
        setIsOpen(!isOpen);
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
        <Tooltip open={isOpen} onOpenChange={handleOpenChange}>
            <TooltipTrigger asChild>
                <button
                    onClick={handleClick}
                    onPointerDown={(e) => e.preventDefault()}
                    className={cn(
                        'inline-flex items-center justify-center rounded-full hover:bg-accent p-1 transition-colors',
                        className
                    )}
                    aria-label="View track details"
                    type="button"
                >
                    <Info className="w-4 h-4 text-muted-foreground" />
                </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="w-[360px] p-0 overflow-hidden" sideOffset={8}>
                {isLoading && (
                    <div className="space-y-2 p-3">
                        {/* Header skeleton */}
                        <div className="space-y-0.5">
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-3 w-1/2" />
                        </div>

                        {/* Divider */}
                        <div className="border-t border-border/50" />

                        {/* Content skeleton */}
                        <div className="flex items-start gap-3">
                            {/* Left side - Details skeleton */}
                            <div className="flex-1 min-w-0 space-y-1.5">
                                <Skeleton className="h-3 w-full" />
                                <Skeleton className="h-3 w-2/3" />
                                <Skeleton className="h-3 w-1/2" />
                                <Skeleton className="h-3 w-3/4" />
                            </div>

                            {/* Right side - Album cover skeleton */}
                            <Skeleton className="w-20 h-20 rounded-md flex-shrink-0" />
                        </div>

                        {/* Button skeleton */}
                        <div className="border-t border-border/50 pt-2">
                            <Skeleton className="h-8 w-full rounded-md" />
                        </div>
                    </div>
                )}
                {error && (
                    <div className="p-4 text-sm text-destructive">
                        {error}
                    </div>
                )}
                {trackDetails && !isLoading && !error && (
                    <div className="space-y-2 p-3">
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
                        <div className="flex items-start gap-3">
                            {/* Left side - Details with icons */}
                            <div className="flex-1 min-w-0 space-y-1.5 text-xs text-foreground/80">
                                {trackDetails.album?.name && (
                                    <div className="flex items-start gap-2">
                                        <Disc className="w-3 h-3 text-muted-foreground/70 flex-shrink-0 mt-0.5" />
                                        <span className="truncate leading-snug">{trackDetails.album.name}</span>
                                    </div>
                                )}

                                {trackDetails.duration_ms && (
                                    <div className="flex items-center gap-2">
                                        <Clock className="w-3 h-3 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-snug">{formatDuration(trackDetails.duration_ms)}</span>
                                    </div>
                                )}

                                {trackDetails.album?.release_date && (
                                    <div className="flex items-center gap-2">
                                        <Calendar className="w-3 h-3 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-snug">{formatReleaseDate(trackDetails.album.release_date)}</span>
                                    </div>
                                )}

                                {trackDetails.track_number && trackDetails.album?.total_tracks && (
                                    <div className="flex items-center gap-2">
                                        <Hash className="w-3 h-3 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-snug">Track {trackDetails.track_number} of {trackDetails.album.total_tracks}</span>
                                    </div>
                                )}

                                {trackDetails.popularity !== undefined && trackDetails.popularity > 0 && (
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="w-3 h-3 text-muted-foreground/70 flex-shrink-0" />
                                        <span className="leading-snug">{trackDetails.popularity}/100</span>
                                    </div>
                                )}

                                {trackDetails.explicit && (
                                    <div className="flex items-center gap-2">
                                        <AlertCircle className="w-3 h-3 text-destructive/80 flex-shrink-0" />
                                        <span className="text-destructive/90 leading-snug">Explicit</span>
                                    </div>
                                )}
                            </div>

                            {/* Right side - Album Cover */}
                            {trackDetails.album_image ? (
                                <div className="w-20 h-20 rounded-md overflow-hidden bg-muted flex-shrink-0 shadow-sm">
                                    <Image
                                        src={trackDetails.album_image}
                                        alt={trackDetails.album.name}
                                        width={80}
                                        height={80}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            ) : (
                                <div className="w-20 h-20 rounded-md bg-muted flex items-center justify-center flex-shrink-0 shadow-sm">
                                    <Music className="w-8 h-8 text-muted-foreground/40" />
                                </div>
                            )}
                        </div>

                        {/* Play on Spotify Button */}
                        <div className="border-t border-border/50 pt-2">
                            <Button
                                size="sm"
                                variant="default"
                                className="w-full h-8 bg-[#1DB954] hover:bg-[#1ed760] text-white text-xs"
                                asChild
                            >
                                <a
                                    href={trackDetails.spotify_url || `https://open.spotify.com/track/${trackDetails.track_id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center justify-center gap-1.5"
                                >
                                    <svg
                                        className="w-3.5 h-3.5"
                                        viewBox="0 0 24 24"
                                        fill="currentColor"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
                                    </svg>
                                    Play on Spotify
                                </a>
                            </Button>
                        </div>
                    </div>
                )}
            </TooltipContent>
        </Tooltip>
    );
}

