'use client';

import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodCard from '@/components/features/mood/MoodCard';
import { useAuth } from '@/lib/contexts/AuthContext';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { shuffleArray } from '@/lib/utils/array';
import { motion } from '@/components/ui/lazy-motion';
import { useRouter } from 'next/navigation';
import { useRef, useState, useMemo } from 'react';


export default function SampleMoods() {
  const containerRef = useRef(null);
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
      {/* Login Dialog */}
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

      {/* Sample Moods Section */}
      <div ref={containerRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="flex flex-col items-center">
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <h2 className="text-3xl font-bold mb-2">
              Sample Moods
            </h2>
            <p className="text-muted-foreground text-md">
              Get inspired by some of these mood templates
            </p>
          </motion.div>
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-6xl w-full"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          >
            {moodExamples.map((template, index) => {
              const hiddenOnMobile = index > 3;
              return (
                <motion.div
                  key={template.name}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
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
          </motion.div>
        </div>
      </div>
    </>
  );
}

