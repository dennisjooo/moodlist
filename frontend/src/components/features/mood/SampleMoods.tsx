'use client';

import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodCard from '@/components/features/mood/MoodCard';
import { motion } from '@/components/ui/lazy-motion';
import { useAuth } from '@/lib/contexts/AuthContext';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { shuffleArray } from '@/lib/utils/array';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

export default function SampleMoods() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [showLoginDialog, setShowLoginDialog] = useState(false);

  const moodExamples = useMemo(() => shuffleArray(MOOD_TEMPLATES).slice(0, 8), []);

  const handleMoodClick = (prompt: string) => {
    if (!isAuthenticated) {
      setShowLoginDialog(true);
      return;
    }

    router.push(`/create?mood=${encodeURIComponent(prompt)}`);
  };

  return (
    <>
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

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
              Templates on deck
            </span>
            <h3 className="mt-6 text-3xl font-semibold sm:text-4xl">Shuffle through sample moods</h3>
            <p className="mt-3 text-base text-muted-foreground">
              Every click spins up a ready-to-use mood template. Pick one that fits, or remix it into something brand new.
            </p>
          </motion.div>

          <div className="mt-12 grid grid-cols-2 gap-6 md:grid-cols-4">
            {moodExamples.map((template, index) => {
              const hiddenOnMobile = index > 3;
              return (
                <motion.div
                  key={template.name}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.5, delay: index * 0.08, ease: 'easeOut' }}
                >
                  <MoodCard
                    name={template.name}
                    description={template.prompt}
                    icon={template.icon}
                    genre={template.genre}
                    gradient={template.gradient}
                    onClick={() => handleMoodClick(template.prompt)}
                    className={hiddenOnMobile ? 'hidden md:flex' : ''}
                  />
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}
