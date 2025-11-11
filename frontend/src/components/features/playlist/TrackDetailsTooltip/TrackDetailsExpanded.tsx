import { AlertCircle, Calendar, Clock, Disc, Hash, Music, TrendingUp, ChevronDown } from 'lucide-react';
import Image from 'next/image';
import { TrackDetails } from '@/lib/api/spotify';
import { DetailRow } from '@/components/ui/detail-row';
import { formatDuration, formatReleaseDate } from '@/lib/utils/format';
import { SpotifyPlayButton } from './SpotifyPlayButton';

interface TrackDetailsExpandedProps {
    trackDetails: TrackDetails;
    onClick: (e: React.MouseEvent) => void;
}

export function TrackDetailsExpanded({ trackDetails, onClick }: TrackDetailsExpandedProps) {
    return (
        <div className="w-[400px] bg-background/95 backdrop-blur-sm rounded-lg p-4 space-y-4">
            {/* Header with album art */}
            <div className="flex gap-3">
                {trackDetails.album_image ? (
                    <div className="w-20 h-20 rounded-md overflow-hidden bg-muted flex-shrink-0 shadow-md">
                        <Image
                            src={trackDetails.album_image}
                            alt={trackDetails.album?.name || 'Album art'}
                            width={80}
                            height={80}
                            className="w-full h-full object-cover"
                        />
                    </div>
                ) : (
                    <div className="w-20 h-20 rounded-md bg-muted flex items-center justify-center flex-shrink-0 shadow-md">
                        <Music className="w-8 h-8 text-muted-foreground/40" />
                    </div>
                )}

                <div className="flex-1 min-w-0 space-y-1">
                    <h4 className="font-semibold text-sm leading-tight line-clamp-2">
                        {trackDetails.track_name}
                    </h4>
                    <p className="text-xs text-muted-foreground line-clamp-1">
                        {trackDetails.artists.map(a => a.name).join(', ')}
                    </p>
                    {trackDetails.album?.name && (
                        <p className="text-xs text-muted-foreground/70 line-clamp-1">
                            {trackDetails.album.name}
                        </p>
                    )}
                </div>
            </div>

            {/* Divider */}
            <div className="border-t border-border/50" />

            {/* Details grid */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-xs">
                {trackDetails.duration_ms && (
                    <DetailRow icon={Clock}>{formatDuration(trackDetails.duration_ms)}</DetailRow>
                )}
                {trackDetails.album?.release_date && (
                    <DetailRow icon={Calendar}>{formatReleaseDate(trackDetails.album.release_date)}</DetailRow>
                )}
                {trackDetails.track_number && trackDetails.album?.total_tracks && (
                    <DetailRow icon={Hash}>
                        Track {trackDetails.track_number}/{trackDetails.album.total_tracks}
                    </DetailRow>
                )}
                {trackDetails.popularity !== undefined && trackDetails.popularity > 0 && (
                    <DetailRow icon={TrendingUp}> {trackDetails.popularity}</DetailRow>
                )}
                {trackDetails.explicit && (
                    <DetailRow icon={AlertCircle} className="text-destructive/90">
                        Explicit
                    </DetailRow>
                )}
            </div>

            {/* Spotify button */}
            <SpotifyPlayButton
                spotifyUrl={trackDetails.spotify_url || `https://open.spotify.com/track/${trackDetails.track_id}`}
            />

            {/* Click to collapse hint */}
            <div className="flex items-center justify-center pt-2 border-t border-border/50">
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                    Click to collapse
                    <ChevronDown className="w-3 h-3 rotate-180" />
                </span>
            </div>
        </div>
    );
}

