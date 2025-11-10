'use client';

import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodCard from '@/components/features/marketing/SampleMoods/MoodCard';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { motion } from '@/components/ui/lazy-motion';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { useAuth } from '@/lib/store/authStore';
import { cn } from '@/lib/utils';
import { shuffleArray } from '@/lib/utils/array';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

interface SampleMoodsProps {
  requireAuth?: boolean;
  maxCards?: number;
  showHeader?: boolean;
  heading?: string;
  description?: string;
  badgeText?: string | null;
  containerClassName?: string;
  gridClassName?: string;
  contentClassName?: string;
  cardClassName?: string;
  showAllOnMobile?: boolean;
  onMoodSelect?: (prompt: string) => void;
}

export default function SampleMoods({
  requireAuth = true,
  maxCards = 8,
  showHeader = true,
  heading = 'Shuffle through sample moods',
  description = 'Every click spins up a ready-to-use mood template. Pick one that fits, or remix it into something brand new.',
  badgeText = 'Templates on deck',
  containerClassName,
  gridClassName,
  contentClassName,
  cardClassName,
  showAllOnMobile = false,
  onMoodSelect,
}: SampleMoodsProps = {}) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [showLoginDialog, setShowLoginDialog] = useState(false);

  const moodExamples = useMemo(
    () => shuffleArray(MOOD_TEMPLATES).slice(0, maxCards),
    [maxCards],
  );

  const handleMoodClick = (prompt: string) => {
    if (onMoodSelect) {
      onMoodSelect(prompt);
      return;
    }

    if (requireAuth && !isAuthenticated) {
      setShowLoginDialog(true);
      return;
    }

    router.push(`/create?mood=${encodeURIComponent(prompt)}`);
  };

  return (
    <>
      {requireAuth && (
        <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />
      )}

      <section className={cn('relative overflow-hidden', containerClassName)}>
        <div className="absolute inset-0 -z-10" />
        <div
          className={cn(
            'relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 lg:px-8',
            contentClassName,
          )}
        >
          {showHeader && (
            <motion.div
              className="mx-auto max-w-3xl text-center"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            >
              {badgeText && (
                <FeatureBadge>
                  {badgeText}
                </FeatureBadge>
              )}
              <h3 className="mt-6 text-3xl font-semibold sm:text-4xl">{heading}</h3>
              <p className="mt-3 text-base text-muted-foreground">
                {description}
              </p>
            </motion.div>
          )}

          <div className={cn('mt-12 grid grid-cols gap-6 md:grid-cols-4', gridClassName)}>
            {moodExamples.map((template, index) => {
              const hiddenOnMobile = !showAllOnMobile && index > 3;
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
                    className={cn(hiddenOnMobile ? 'hidden md:flex' : '', cardClassName)}
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
