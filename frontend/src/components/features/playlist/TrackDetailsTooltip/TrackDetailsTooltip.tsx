'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Info } from 'lucide-react';
import { memo, useState } from 'react';
import { TrackDetailsLoadingSkeleton } from '../../../shared/LoadingStates/Skeletons';
import { useTrackDetails } from '@/lib/hooks/playlist/useTrackDetails';
import { TrackDetailsCompactCard } from './TrackDetailsCompactCard';
import { TrackDetailsExpanded } from './TrackDetailsExpanded';

interface TrackDetailsTooltipProps {
    spotifyUri: string;
    className?: string;
}

function TrackDetailsTooltip({ spotifyUri, className }: TrackDetailsTooltipProps) {
    const { trackDetails, isLoading, error, loadTrackDetails } = useTrackDetails();
    const [isOpen, setIsOpen] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);

    const handleOpenChange = async (open: boolean) => {
        setIsOpen(open);
        if (!open) {
            setIsExpanded(false);
            return;
        }
        await loadTrackDetails(spotifyUri);
    };

    const handleTriggerClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (isOpen) {
            setIsOpen(false);
        } else {
            setIsOpen(true);
            handleOpenChange(true);
        }
    };

    const handleCardClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsExpanded(!isExpanded);
    };

    return (
        <Tooltip open={isOpen} onOpenChange={handleOpenChange}>
            <TooltipTrigger
                onClick={handleTriggerClick}
                onPointerDown={(e) => e.preventDefault()}
                className={cn(
                    'inline-flex items-center justify-center rounded-full hover:bg-accent p-1 transition-colors',
                    className
                )}
                aria-label="View track details"
            >
                <Info className="w-4 h-4 text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent
                side="top"
                className={cn(
                    "p-0 overflow-hidden transition-all duration-300 ease-out",
                    isExpanded ? "w-[400px]" : "w-[280px]",
                    !isExpanded && "bg-transparent border-none shadow-none"
                )}
                sideOffset={8}
            >
                {isLoading && (
                    <div className="animate-in fade-in-0 duration-200">
                        <TrackDetailsLoadingSkeleton />
                    </div>
                )}
                {error && (
                    <div className="p-4 text-sm text-destructive animate-in fade-in-0 duration-200">
                        {error}
                    </div>
                )}
                {trackDetails && (
                    <div
                        className={cn(
                            "cursor-pointer transition-all duration-300 animate-in fade-in-0",
                            "hover:bg-accent/5",
                            !isExpanded && "group"
                        )}
                        onClick={handleCardClick}
                    >
                        {!isExpanded ? (
                            <TrackDetailsCompactCard trackDetails={trackDetails} onClick={handleCardClick} />
                        ) : (
                            <TrackDetailsExpanded trackDetails={trackDetails} onClick={handleCardClick} />
                        )}
                    </div>
                )}
            </TooltipContent>
        </Tooltip>
    );
}

export default memo(TrackDetailsTooltip);

