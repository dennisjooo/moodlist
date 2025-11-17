'use client';

import type { Track } from '@/lib/types/workflow';
import TrackRow from '@/components/shared/TrackRow';

interface TrackCardProps {
    track: Track;
    index: number;
    isNew: boolean;
}

export function TrackCard({ track, index, isNew }: TrackCardProps) {
    return <TrackRow track={track} index={index} isNew={isNew} showSource />;
}
