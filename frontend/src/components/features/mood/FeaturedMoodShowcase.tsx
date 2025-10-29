'use client';

import { AnimatePresence, motion } from '@/components/ui/lazy-motion';
import {
  FEATURED_MOOD_FEATURES,
  FEATURED_MOOD_SHOWCASE,
  FEATURED_MOOD_TRACKS,
} from '@/lib/constants/sampleMoodShowcase';
import { useEffect, useState } from 'react';

const SHOWCASE_GRADIENT = {
  background: `linear-gradient(135deg, ${FEATURED_MOOD_SHOWCASE.colorScheme.primary}, ${FEATURED_MOOD_SHOWCASE.colorScheme.secondary})`,
  boxShadow: `0 32px 60px -32px ${FEATURED_MOOD_SHOWCASE.colorScheme.primary}AA`,
};

const formatMetricRange = (range: [number, number], unit?: string) => {
  const [min, max] = range;

  if (unit === 'BPM') {
    return `${Math.round(min)}–${Math.round(max)} ${unit}`;
  }

  if (unit === 'dB') {
    return `${min.toFixed(0)} to ${max.toFixed(0)} ${unit}`;
  }

  return `${Math.round(min * 100)}–${Math.round(max * 100)}%`;
};

const asPercent = (value: number) => `${Math.round(value * 100)}%`;

export default function FeaturedMoodShowcase() {
  const [currentFeatureIndex, setCurrentFeatureIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFeatureIndex((prev) => (prev + 1) % FEATURED_MOOD_FEATURES.length);
    }, 3500);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10" />
      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 lg:px-8">
        <motion.div
          className="mx-auto max-w-3xl text-center"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1 text-sm font-medium text-primary">
            Live mood walkthrough
          </span>
          <h2 className="mt-6 text-3xl font-semibold sm:text-4xl">See how Moodlist builds a vibe</h2>
          <p className="mt-3 text-base text-muted-foreground">
            Peek at a real mood prompt, the AI interpretation, and the tracks it surfaces—then try your own twist.
          </p>
        </motion.div>

        <div className="mt-14 grid gap-6 lg:grid-cols-12">
          <motion.article
            className="relative overflow-hidden rounded-3xl border border-white/5 p-8 text-left text-white shadow-xl lg:col-span-4"
            style={SHOWCASE_GRADIENT}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-widest opacity-90">Featured prompt</p>
                <h3 className="mt-2 text-2xl font-semibold">{FEATURED_MOOD_SHOWCASE.name}</h3>
              </div>
              <div className="h-14 w-14 rounded-full border border-white/40 bg-white/10" aria-hidden />
            </div>
            <p className="mt-6 text-base leading-relaxed">"{FEATURED_MOOD_SHOWCASE.prompt}"</p>
            <div className="mt-6 space-y-3">
              {FEATURED_MOOD_SHOWCASE.summaryHighlights.map((highlight) => (
                <div key={highlight} className="flex items-start gap-3 text-sm">
                  <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-white" />
                  <p className="opacity-90">{highlight}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {FEATURED_MOOD_SHOWCASE.keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-full border border-white/40 bg-white/15 px-3 py-1 text-xs font-medium uppercase tracking-widest"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </motion.article>

          <motion.div
            className="rounded-3xl border border-border/60 bg-background/70 p-8 backdrop-blur lg:col-span-4"
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, delay: 0.1, ease: 'easeOut' }}
          >
            <p className="text-sm font-semibold uppercase tracking-widest text-primary">AI reads it as</p>
            <p className="mt-3 text-lg font-medium text-foreground">{FEATURED_MOOD_SHOWCASE.moodInterpretation}</p>
            <dl className="mt-6 space-y-4">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Primary emotion</dt>
                <dd className="text-sm font-medium text-foreground">{FEATURED_MOOD_SHOWCASE.primaryEmotion}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Energy level</dt>
                <dd className="text-sm font-medium text-foreground">{FEATURED_MOOD_SHOWCASE.energyLevel}</dd>
              </div>
            </dl>
            <div className="mt-6 relative">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground">
                  Audio features {currentFeatureIndex + 1}/{FEATURED_MOOD_FEATURES.length}
                </span>
                <div className="flex gap-1">
                  {FEATURED_MOOD_FEATURES.map((_, index) => (
                    <button
                      key={index}
                      onClick={() => setCurrentFeatureIndex(index)}
                      className={`h-1.5 rounded-full transition-all ${index === currentFeatureIndex
                        ? 'w-6 bg-primary'
                        : 'w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/50'
                        }`}
                      aria-label={`Go to feature ${index + 1}`}
                    />
                  ))}
                </div>
              </div>
              <div className="relative h-32 overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentFeatureIndex}
                    className="absolute inset-0 rounded-2xl border border-dashed border-primary/40 bg-primary/5 p-4"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.4, ease: 'easeInOut' }}
                  >
                    <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                      {FEATURED_MOOD_FEATURES[currentFeatureIndex].label}
                    </p>
                    <p className="mt-1 text-sm font-medium text-foreground">
                      {formatMetricRange(
                        FEATURED_MOOD_FEATURES[currentFeatureIndex].range,
                        FEATURED_MOOD_FEATURES[currentFeatureIndex].unit
                      )}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {FEATURED_MOOD_FEATURES[currentFeatureIndex].description}
                    </p>
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </motion.div>

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
              {FEATURED_MOOD_TRACKS.map((track, index) => (
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
                    <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">{index + 1}</span>
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
        </div>
      </div>
    </section>
  );
}

