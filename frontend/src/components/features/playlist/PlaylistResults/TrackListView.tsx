'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { motion } from '@/components/ui/lazy-motion';
import { CARD_FADE_IN_UP_LONG_DELAY_VARIANTS, TRACK_LIST_STAGGER_CONTAINER_VARIANTS } from '@/lib/constants/animations';
import { VirtualTrackList } from '@/components/shared/VirtualTrackList';
import { Track } from '@/lib/types/track';
import TrackRow from '@/components/shared/TrackRow';

interface TrackListViewProps {
  tracks: Track[];
}

const VIRTUALIZATION_THRESHOLD = 50; // Use virtualization for 50+ tracks

export default function TrackListView({ tracks }: TrackListViewProps) {
  // Use virtualization for large lists to improve performance
  if (tracks.length > VIRTUALIZATION_THRESHOLD) {
    return (
      <motion.div
        variants={CARD_FADE_IN_UP_LONG_DELAY_VARIANTS}
        initial="hidden"
        animate="visible"
      >
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
      </motion.div>
    );
  }

  // Use regular rendering for smaller lists
  return (
    <motion.div
      variants={CARD_FADE_IN_UP_LONG_DELAY_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommended Tracks</CardTitle>
        </CardHeader>
        <CardContent>
          <motion.div
            className="space-y-2"
            variants={TRACK_LIST_STAGGER_CONTAINER_VARIANTS}
            initial="hidden"
            animate="visible"
          >
            {tracks.map((track, index) => (
              <TrackRow
                key={`track-${index}-${track.track_id}`}
                track={track}
                index={index}
              />
            ))}
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

