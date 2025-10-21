'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import TrackRow from './TrackRow';

interface Track {
  track_id: string;
  track_name: string;
  artists: string[];
  confidence_score: number;
  spotify_uri?: string;
}

interface TrackListViewProps {
  tracks: Track[];
}

export default function TrackListView({ tracks }: TrackListViewProps) {
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

