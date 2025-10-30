'use client';

import { motion } from '@/components/ui/lazy-motion';

const asPercent = (value: number) => `${Math.round(value * 100)}%`;

interface Track {
  name: string;
  artists: string;
  spotifyUri: string;
  highlight: string;
  energy: number;
  danceability: number;
  valence: number;
  tempo: number;
}

interface SpotlightTracksCardProps {
  tracks: Track[];
}

export default function SpotlightTracksCard({ tracks }: SpotlightTracksCardProps) {
  return (
    <motion.div
      className="rounded-3xl border border-border/60 bg-background/70 p-8 backdrop-blur lg:col-span-4"
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay: 0.15, ease: 'easeOut' }}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold uppercase tracking-widest text-primary">Spotlight tracks</p>
        <span className="text-xs text-muted-foreground">From a real session</span>
      </div>
      <ul className="mt-6 space-y-4">
        {tracks.map((track, index) => (
          <motion.li
            key={track.spotifyUri}
            className="group relative overflow-hidden rounded-2xl border border-border/60 bg-background/60 p-4"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.45, delay: index * 0.08, ease: 'easeOut' }}
            whileHover={{ translateY: -4 }}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-foreground">{track.name}</p>
                <p className="text-xs text-muted-foreground">{track.artists}</p>
              </div>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                {index + 1}
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">{track.highlight}</p>
            <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-medium text-muted-foreground">
              <span className="rounded-full bg-muted px-2 py-1">Energy {asPercent(track.energy)}</span>
              <span className="rounded-full bg-muted px-2 py-1">Dance {asPercent(track.danceability)}</span>
              <span className="rounded-full bg-muted px-2 py-1">Valence {asPercent(track.valence)}</span>
              <span className="rounded-full bg-muted px-2 py-1">{Math.round(track.tempo)} BPM</span>
            </div>
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}

