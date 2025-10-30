'use client';

import { AnimatePresence, motion } from '@/components/ui/lazy-motion';
import { FEATURED_MOOD_SHOWCASES } from '@/lib/constants/sampleMoodShowcase';

const getShowcaseGradient = (showcase: typeof FEATURED_MOOD_SHOWCASES[0]) => ({
  background: `linear-gradient(135deg, ${showcase.colorScheme.primary}, ${showcase.colorScheme.secondary})`,
  boxShadow: `0 32px 60px -32px ${showcase.colorScheme.primary}AA`,
});

interface FeaturedPromptCardProps {
  showcase: typeof FEATURED_MOOD_SHOWCASES[0];
  showcaseIndex: number;
  totalShowcases: number;
  onPrevious: () => void;
  onNext: () => void;
}

export default function FeaturedPromptCard({
  showcase,
  showcaseIndex,
  totalShowcases,
  onPrevious,
  onNext,
}: FeaturedPromptCardProps) {
  return (
    <div className="relative flex lg:col-span-4">
      <AnimatePresence mode="wait">
        <motion.article
          key={showcaseIndex}
          className="relative flex w-full flex-col overflow-hidden rounded-3xl border border-white/5 p-8 text-left text-white shadow-xl"
          style={getShowcaseGradient(showcase)}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.4, ease: 'easeInOut' }}
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-widest opacity-90">Featured prompt</p>
              <h3 className="mt-2 text-2xl font-semibold">{showcase.name}</h3>
            </div>
            <div className="h-14 w-14 rounded-full border border-white/40 bg-white/10" aria-hidden />
          </div>
          <p className="mt-6 text-base leading-relaxed">&quot;{showcase.prompt}&quot;</p>
          <div className="mt-6 space-y-3">
            {showcase.summaryHighlights.map((highlight) => (
              <div key={highlight} className="flex items-start gap-3 text-sm">
                <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-white" />
                <p className="opacity-90">{highlight}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {showcase.keywords.map((keyword) => (
              <span
                key={keyword}
                className="rounded-full border border-white/40 bg-white/15 px-3 py-1 text-xs font-medium uppercase tracking-widest"
              >
                {keyword}
              </span>
            ))}
          </div>
          <div className="mt-auto pt-8 flex items-center justify-between gap-4">
            <button
              onClick={onPrevious}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-white/40 bg-white/10 transition-all hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
              aria-label="Previous mood showcase"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-5 w-5"
              >
                <path
                  fillRule="evenodd"
                  d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
            <div className="flex gap-1">
              {Array.from({ length: totalShowcases }).map((_, index) => (
                <div
                  key={index}
                  className={`h-1.5 rounded-full transition-all ${
                    index === showcaseIndex ? 'w-6 bg-white' : 'w-1.5 bg-white/40'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={onNext}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-white/40 bg-white/10 transition-all hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
              aria-label="Next mood showcase"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-5 w-5"
              >
                <path
                  fillRule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </motion.article>
      </AnimatePresence>
    </div>
  );
}

