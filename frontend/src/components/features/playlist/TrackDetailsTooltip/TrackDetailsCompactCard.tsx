import { Disc, Music, ChevronDown } from 'lucide-react';
import { TrackDetails } from '@/lib/api/spotify';
import TiltedCard from '@/components/ui/tilted-card';

interface TrackDetailsCompactCardProps {
    trackDetails: TrackDetails;
    onClick: (e: React.MouseEvent) => void;
}

export function TrackDetailsCompactCard({ trackDetails, onClick }: TrackDetailsCompactCardProps) {
    return (
        <div className="relative w-[280px] h-[280px]">
            {trackDetails.album_image ? (
                <>
                    <TiltedCard
                        imageSrc={trackDetails.album_image}
                        altText={trackDetails.album?.name || 'Album art'}
                        containerHeight="280px"
                        containerWidth="280px"
                        imageHeight="280px"
                        imageWidth="280px"
                        scaleOnHover={1.12}
                        rotateAmplitude={12}
                        showMobileWarning={false}
                        showTooltip={false}
                        displayOverlayContent={true}
                        overlayContent={
                            <div className="w-[280px] h-[280px] pointer-events-none">
                                <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/80 via-black/40 to-transparent rounded-b-[14px]" />
                            </div>
                        }
                    />
                    {/* Fixed text overlay that doesn't tilt */}
                    <div className="absolute inset-0 pointer-events-none">
                        <div className="relative z-10 h-full flex flex-col justify-end p-4 space-y-1">
                            <h4 className="font-semibold text-sm leading-tight line-clamp-2 text-white drop-shadow-lg">
                                {trackDetails.track_name}
                            </h4>
                            <p className="text-xs text-white/90 line-clamp-1 drop-shadow-md">
                                {trackDetails.artists.map(a => a.name).join(', ')}
                            </p>
                            {trackDetails.album?.name && (
                                <p className="text-xs text-white/80 line-clamp-1 flex items-center gap-1 drop-shadow-md">
                                    <Disc className="w-3 h-3 flex-shrink-0" />
                                    <span className="truncate">{trackDetails.album.name}</span>
                                </p>
                            )}
                            <div className="pt-2 flex items-center justify-center">
                                <span className="text-xs text-white/70 flex items-center gap-1 drop-shadow-md">
                                    Click for details
                                    <ChevronDown className="w-3 h-3" />
                                </span>
                            </div>
                        </div>
                    </div>
                </>
            ) : (
                <div className="w-[280px] h-[280px] rounded-lg bg-muted flex flex-col items-center justify-center p-4">
                    <Music className="w-16 h-16 text-muted-foreground/40 mb-4" />
                    <h4 className="font-semibold text-sm text-center line-clamp-2">
                        {trackDetails.track_name}
                    </h4>
                    <p className="text-xs text-muted-foreground text-center line-clamp-1 mt-1">
                        {trackDetails.artists.map(a => a.name).join(', ')}
                    </p>
                </div>
            )}
        </div>
    );
}

