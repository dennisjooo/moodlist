'use client';

import LoginRequiredDialog from '@/components/LoginRequiredDialog';
import MoodCard from '@/components/features/mood/MoodCard';
import { useAuth } from '@/lib/contexts/AuthContext';
import { getMoodGenre } from '@/lib/moodColors';
import { MOOD_TEMPLATES } from '@/lib/constants/moodTemplates';
import { motion } from '@/components/ui/lazy-motion';
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';


export default function PopularMoods() {
  const containerRef = useRef(null);
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [showLoginDialog, setShowLoginDialog] = useState(false);

  const moodExamples = MOOD_TEMPLATES.slice(0, 8);

  const handleMoodClick = (prompt: string, label: string) => {
    if (!isAuthenticated) {
      setShowLoginDialog(true);
      return;
    }

    router.push(`/create?mood=${encodeURIComponent(prompt || `${label} in the genre of ${getMoodGenre(label)}`)}`);
  };

  return (
    <>
      {/* Login Dialog */}
      <LoginRequiredDialog open={showLoginDialog} onOpenChange={setShowLoginDialog} />

      {/* Popular Moods Section */}
      <div ref={containerRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-16">
        <div className="flex flex-col items-center">
          <motion.h2
            className="text-2xl font-semibold text-center mb-8"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            Popular Moods
          </motion.h2>
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
                    mood={`${template.emoji} ${template.name}`}
                    onClick={() => handleMoodClick(template.prompt, template.name)}
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

