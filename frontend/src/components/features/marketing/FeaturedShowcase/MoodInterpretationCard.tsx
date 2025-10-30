'use client';

import { AnimatePresence, motion } from '@/components/ui/lazy-motion';

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

interface AudioFeature {
  label: string;
  range: [number, number];
  unit?: string;
  description: string;
}

interface MoodInterpretationCardProps {
  moodInterpretation: string;
  primaryEmotion: string;
  energyLevel: string;
  features: AudioFeature[];
  currentFeatureIndex: number;
  onFeatureChange: (index: number) => void;
}

export default function MoodInterpretationCard({
  moodInterpretation,
  primaryEmotion,
  energyLevel,
  features,
  currentFeatureIndex,
  onFeatureChange,
}: MoodInterpretationCardProps) {
  return (
    <motion.div
      className="rounded-3xl border border-border/60 bg-background/70 p-8 backdrop-blur lg:col-span-4"
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay: 0.1, ease: 'easeOut' }}
    >
      <p className="text-sm font-semibold uppercase tracking-widest text-primary">AI reads it as</p>
      <p className="mt-3 text-lg font-medium text-foreground">{moodInterpretation}</p>
      <dl className="mt-6 space-y-4">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Primary emotion</dt>
          <dd className="text-sm font-medium text-foreground">{primaryEmotion}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Energy level</dt>
          <dd className="text-sm font-medium text-foreground">{energyLevel}</dd>
        </div>
      </dl>
      <div className="mt-6 relative">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-muted-foreground">
            Audio features {currentFeatureIndex + 1}/{features.length}
          </span>
          <div className="flex gap-1">
            {features.map((_, index) => (
              <button
                key={index}
                onClick={() => onFeatureChange(index)}
                className={`h-1.5 rounded-full transition-all ${
                  index === currentFeatureIndex
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
                {features[currentFeatureIndex].label}
              </p>
              <p className="mt-1 text-sm font-medium text-foreground">
                {formatMetricRange(features[currentFeatureIndex].range, features[currentFeatureIndex].unit)}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{features[currentFeatureIndex].description}</p>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

