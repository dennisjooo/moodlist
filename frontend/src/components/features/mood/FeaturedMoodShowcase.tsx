'use client';

import { motion } from '@/components/ui/lazy-motion';
import {
  FEATURED_MOOD_FEATURES_ARRAYS,
  FEATURED_MOOD_SHOWCASES,
  FEATURED_MOOD_TRACKS_ARRAYS,
} from '@/lib/constants/sampleMoodShowcase';
import { getRandomIndex } from '@/lib/utils/array';
import { useEffect, useMemo, useState } from 'react';
import FeaturedPromptCard from './FeaturedPromptCard';
import MoodInterpretationCard from './MoodInterpretationCard';
import SpotlightTracksCard from './SpotlightTracksCard';

export default function FeaturedMoodShowcase() {
  const [currentFeatureIndex, setCurrentFeatureIndex] = useState(0);
  const [selectedShowcaseIndex, setSelectedShowcaseIndex] = useState(0);

  useEffect(() => {
    // Randomly select a showcase on component mount
    setSelectedShowcaseIndex(getRandomIndex(FEATURED_MOOD_SHOWCASES));
  }, []);

  const selectedShowcaseData = useMemo(() => {
    const showcase = FEATURED_MOOD_SHOWCASES[selectedShowcaseIndex];
    const features = FEATURED_MOOD_FEATURES_ARRAYS[selectedShowcaseIndex];
    const tracks = FEATURED_MOOD_TRACKS_ARRAYS[selectedShowcaseIndex];
    return { showcase, features, tracks };
  }, [selectedShowcaseIndex]);

  const handlePreviousShowcase = () => {
    setSelectedShowcaseIndex((prev) => (prev - 1 + FEATURED_MOOD_SHOWCASES.length) % FEATURED_MOOD_SHOWCASES.length);
    setCurrentFeatureIndex(0); // Reset feature index when changing showcase
  };

  const handleNextShowcase = () => {
    setSelectedShowcaseIndex((prev) => (prev + 1) % FEATURED_MOOD_SHOWCASES.length);
    setCurrentFeatureIndex(0); // Reset feature index when changing showcase
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFeatureIndex((prev) => (prev + 1) % selectedShowcaseData.features.length);
    }, 3500);

    return () => clearInterval(interval);
  }, [selectedShowcaseData.features.length]);

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

        <div className="mt-14 grid gap-6 lg:grid-cols-12 lg:items-stretch">
          <FeaturedPromptCard
            showcase={selectedShowcaseData.showcase}
            showcaseIndex={selectedShowcaseIndex}
            totalShowcases={FEATURED_MOOD_SHOWCASES.length}
            onPrevious={handlePreviousShowcase}
            onNext={handleNextShowcase}
          />

          <MoodInterpretationCard
            moodInterpretation={selectedShowcaseData.showcase.moodInterpretation}
            primaryEmotion={selectedShowcaseData.showcase.primaryEmotion}
            energyLevel={selectedShowcaseData.showcase.energyLevel}
            features={selectedShowcaseData.features}
            currentFeatureIndex={currentFeatureIndex}
            onFeatureChange={setCurrentFeatureIndex}
          />

          <SpotlightTracksCard tracks={selectedShowcaseData.tracks} />
        </div>
      </div>
    </section>
  );
}

