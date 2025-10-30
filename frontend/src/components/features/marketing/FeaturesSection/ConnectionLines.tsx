'use client';

import { motion } from '@/components/ui/lazy-motion';

export function ConnectionLines() {
  return (
    <div className="hidden md:block absolute top-24 left-0 right-0 pointer-events-none z-0">
      <div className="max-w-6xl mx-auto px-12 flex items-center justify-between">
        {[0.3, 0.5].map((delay, i) => (
          <motion.div
            key={i}
            className="flex-1 h-0.5 bg-gradient-to-r from-transparent via-primary/60 to-transparent mx-8 shadow-[0_0_8px_rgba(var(--primary-rgb),0.4)]"
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.8, delay }}
          />
        ))}
      </div>
    </div>
  );
}

