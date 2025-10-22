'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { VirtualTrackList } from '@/components/shared/VirtualTrackList';
import { Track } from '@/lib/types/track';
import TrackRow from './TrackRow';

interface TrackListViewProps {
  tracks: Track[];
}

const VIRTUALIZATION_THRESHOLD = 50; // Use virtualization for 50+ tracks

export default function TrackListView({ tracks }: TrackListViewProps) {
  // Use virtualization for large lists to improve performance
  if (tracks.length > VIRTUALIZATION_THRESHOLD) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Tracks ({tracks.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <VirtualTrackList
            tracks={tracks}
            itemHeight={60}
            containerHeight={400}
            className="space-y-2"
            renderTrack={(track, index, isFocused) => (
              <TrackRow
                key={`track-${index}-${track.track_id}`}
                track={track}
                index={index}
                isFocused={isFocused}
              />
            )}
          />
        </CardContent>
      </Card>
    );
  }

  // Use regular rendering for smaller lists
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Recommended Tracks</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {tracks.map((track, index) => (
            <TrackRow
              key={`track-${index}-${track.track_id}`}
              track={track}
              index={index}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

