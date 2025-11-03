'use client';

import { DetailRow } from '@/components/ui/detail-row';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { spotifyAPI, TrackDetails } from '@/lib/api/spotify';
import { cn } from '@/lib/utils';
import { formatDuration, formatReleaseDate } from '@/lib/utils/format';
import { logger } from '@/lib/utils/logger';
import { AlertCircle, Calendar, Clock, Disc, Hash, Info, Music, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import { memo, useState } from 'react';
import { TrackDetailsLoadingSkeleton } from '../../shared/LoadingStates/Skeletons';

interface TrackDetailsTooltipProps {
    spotifyUri: string;
    className?: string;
}

function TrackDetailsTooltip({ spotifyUri, className }: TrackDetailsTooltipProps) {
    const [trackDetails, setTrackDetails] = useState<TrackDetails | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    const handleOpenChange = async (open: boolean) => {
        setIsOpen(open);
        if (!open || hasLoaded) return;

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
    };

    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!isOpen) {
            setIsOpen(true);
            handleOpenChange(true);
        }
    };

    return (
        <Tooltip open={isOpen} onOpenChange={handleOpenChange}>
            <TooltipTrigger
                onClick={handleClick}
                className={cn(
                    'inline-flex items-center justify-center rounded-full hover:bg-accent p-1 transition-colors',
                    className
                )}
                aria-label="View track details"
            >
                <Info className="w-4 h-4 text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent side="top" className="w-[360px] p-0 overflow-hidden" sideOffset={8}>
                {isLoading && <TrackDetailsLoadingSkeleton />}
                {error && <div className="p-4 text-sm text-destructive">{error}</div>}
                {trackDetails && (
                    <div className="space-y-2 p-3">
                        <div className="space-y-0.5">
                            <h4 className="font-semibold text-sm leading-tight truncate">
                                {trackDetails.track_name}
                            </h4>
                            <p className="text-xs text-muted-foreground truncate">
                                {trackDetails.artists.map(a => a.name).join(', ')}
                            </p>
                        </div>

                        <div className="border-t border-border/50" />

                        <div className="flex items-start gap-3">
                            <div className="flex-1 min-w-0 space-y-1.5 text-xs text-foreground/80">
                                {trackDetails.album?.name && (
                                    <DetailRow icon={Disc}>
                                        <span className="truncate">{trackDetails.album.name}</span>
                                    </DetailRow>
                                )}
                                {trackDetails.duration_ms && (
                                    <DetailRow icon={Clock}>{formatDuration(trackDetails.duration_ms)}</DetailRow>
                                )}
                                {trackDetails.album?.release_date && (
                                    <DetailRow icon={Calendar}>{formatReleaseDate(trackDetails.album.release_date)}</DetailRow>
                                )}
                                {trackDetails.track_number && trackDetails.album?.total_tracks && (
                                    <DetailRow icon={Hash}>
                                        Track {trackDetails.track_number} of {trackDetails.album.total_tracks}
                                    </DetailRow>
                                )}
                                {trackDetails.popularity !== undefined && trackDetails.popularity > 0 && (
                                    <DetailRow icon={TrendingUp}>{trackDetails.popularity}/100</DetailRow>
                                )}
                                {trackDetails.explicit && (
                                    <DetailRow icon={AlertCircle} className="text-destructive/90">
                                        Explicit
                                    </DetailRow>
                                )}
                            </div>

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

                        <div className="border-t border-border/50 pt-2">
                            <a
                                href={trackDetails.spotify_url || `https://open.spotify.com/track/${trackDetails.track_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-1.5 w-full h-8 bg-[#1DB954] hover:bg-[#1ed760] text-white text-xs rounded-md transition-colors"
                            >
                                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
                                </svg>
                                Play on Spotify
                            </a>
                        </div>
                    </div>
                )}
            </TooltipContent>
        </Tooltip>
    );
}

export default memo(TrackDetailsTooltip);
