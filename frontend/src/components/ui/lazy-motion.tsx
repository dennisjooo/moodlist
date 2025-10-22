/**
 * Lazy-loaded framer-motion components
 * These wrappers allow code-splitting of the framer-motion library
 * Import from this file instead of directly from 'framer-motion'
 */

'use client';

import dynamic from 'next/dynamic';
import { ComponentProps } from 'react';

// Create a loading placeholder for motion components
function MotionPlaceholder({ children, ...props }: any) {
  return <div {...props}>{children}</div>;
}

// Dynamically import motion components with placeholder
export const motion = {
  div: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.div),
    { 
      loading: () => <MotionPlaceholder as="div" />,
      ssr: false 
    }
  ) as any,
  
  span: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.span),
    { 
      loading: () => <MotionPlaceholder as="span" />,
      ssr: false 
    }
  ) as any,
  
  ul: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.ul),
    { 
      loading: () => <MotionPlaceholder as="ul" />,
      ssr: false 
    }
  ) as any,
  
  li: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.li),
    { 
      loading: () => <MotionPlaceholder as="li" />,
      ssr: false 
    }
  ) as any,
  
  button: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.button),
    { 
      loading: () => <MotionPlaceholder as="button" />,
      ssr: false 
    }
  ) as any,
};

// Export commonly used hooks with lazy loading
export { useAnimation, useInView } from 'framer-motion';

// For components that need the full motion library, export a dynamic version
export const LazyMotion = dynamic(
  () => import('framer-motion').then((mod) => ({
    default: mod.motion
  })),
  { ssr: false }
);

