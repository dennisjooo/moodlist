'use client';

import { motion, AnimatePresence } from '@/components/ui/lazy-motion';
import { ReactNode } from 'react';

interface CrossfadeTransitionProps {
  isLoading: boolean;
  skeleton: ReactNode;
  children: ReactNode;
  duration?: number;
}

export function CrossfadeTransition({
  isLoading,
  skeleton,
  children,
  duration = 0.4
}: CrossfadeTransitionProps) {
  return (
    <AnimatePresence mode="wait">
      {isLoading ? (
        <motion.div
          key="skeleton"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration, ease: 'easeInOut' }}
        >
          {skeleton}
        </motion.div>
      ) : (
        <motion.div
          key="content"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration, ease: 'easeInOut' }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
