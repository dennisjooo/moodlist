/**
 * Lazy-loaded framer-motion components
 * These wrappers allow code-splitting of the framer-motion library
 * Import from this file instead of directly from 'framer-motion'
 */

'use client';

import dynamic from 'next/dynamic';
import React, { HTMLAttributes, ReactNode } from 'react';

// Create a loading placeholder for motion components
interface MotionPlaceholderProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
  as?: string;
}

function MotionPlaceholder({ children, as = 'div', ...props }: MotionPlaceholderProps) {
  return React.createElement(as, props, children);
}

// Type definitions for motion components
// Using generic component types that accept motion props
type MotionComponentProps = Record<string, unknown>;
type MotionDivComponent = React.ComponentType<MotionComponentProps>;
type MotionSpanComponent = React.ComponentType<MotionComponentProps>;
type MotionUlComponent = React.ComponentType<MotionComponentProps>;
type MotionLiComponent = React.ComponentType<MotionComponentProps>;
type MotionButtonComponent = React.ComponentType<MotionComponentProps>;

// Dynamically import motion components with placeholder
export const motion = {
  div: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.div),
    {
      loading: () => <MotionPlaceholder as="div" />,
      ssr: false
    }
  ) as MotionDivComponent,

  span: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.span),
    {
      loading: () => <MotionPlaceholder as="span" />,
      ssr: false
    }
  ) as MotionSpanComponent,

  ul: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.ul),
    {
      loading: () => <MotionPlaceholder as="ul" />,
      ssr: false
    }
  ) as MotionUlComponent,

  li: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.li),
    {
      loading: () => <MotionPlaceholder as="li" />,
      ssr: false
    }
  ) as MotionLiComponent,

  button: dynamic(
    () => import('framer-motion').then((mod) => mod.motion.button),
    {
      loading: () => <MotionPlaceholder as="button" />,
      ssr: false
    }
  ) as MotionButtonComponent,
};

// Export commonly used hooks with lazy loading
export { useAnimation, useInView } from 'framer-motion';

