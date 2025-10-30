'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Sparkles } from 'lucide-react';

export function SectionHeader() {
  return (
    <motion.div
      className="mx-auto max-w-3xl text-center mb-16 lg:mb-20"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <motion.span
        className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-medium uppercase tracking-[0.24em] text-primary backdrop-blur shadow-sm"
        whileHover={{ scale: 1.05 }}
        transition={{ duration: 0.2 }}
      >
        <Sparkles className="w-3.5 h-3.5" />
        Simple process
      </motion.span>
      <h2 className="mt-6 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text">
        How It Works
      </h2>
      <p className="mt-4 text-base text-muted-foreground/90 sm:text-lg max-w-2xl mx-auto">
        Three simple steps to transform your mood into the perfect soundtrack
      </p>
    </motion.div>
  );
}

