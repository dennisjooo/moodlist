import MoodCard from '@/components/MoodCard';
import { motion } from 'framer-motion';
import { useRef } from 'react';


export default function PopularMoods() {
  const containerRef = useRef(null);

  // Now we just need mood names - colors and genres are auto-generated!
  const allMoodExamples = [
    'Chill Evening',
    'Workout Energy',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
    'Rainy Day',
    'Party Vibes',
  ];

  // Show only first 4 moods on mobile, all on desktop
  const moodExamples = allMoodExamples;

  return (
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
          {moodExamples.map((mood, index) => {
            // Hide cards beyond index 3 on mobile
            const hiddenOnMobile = index > 3;
            return (
              <motion.div
                key={mood}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
              >
                <MoodCard
                  mood={mood}
                  className={hiddenOnMobile ? 'hidden md:flex' : ''}
                />
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}