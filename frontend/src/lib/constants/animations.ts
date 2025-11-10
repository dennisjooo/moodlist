/**
 * Shared animation constants and presets
 * Centralizes framer-motion animation configurations
 */

import type { Transition, Variants } from 'framer-motion';

// Spring transition presets
export const SPRING_TRANSITIONS = {
  gentle: { type: "spring", stiffness: 400, damping: 17 } as Transition,
  snappy: { type: "spring", stiffness: 500, damping: 30 } as Transition,
} as const;

// Common motion props for buttons
export const BUTTON_MOTION_PROPS = {
  whileHover: { scale: 1.05 },
  whileTap: { scale: 0.95 },
} as const;

export const SUBTLE_BUTTON_MOTION_PROPS = {
  whileHover: { scale: 1.02 },
  whileTap: { scale: 0.98 },
} as const;

// Dropdown/Menu animation variants
export const DROPDOWN_VARIANTS: Variants = {
  closed: {
    opacity: 0,
    y: -10,
    scale: 0.95,
    transition: {
      duration: 0.15,
    },
  },
  open: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.15,
    },
  },
};

// Mobile menu animation variants
export const MOBILE_MENU_VARIANTS: Variants = {
  closed: {
    opacity: 0,
    y: -20,
    scale: 0.95,
    transition: {
      duration: 0.2,
      ease: [0.4, 0, 0.6, 1],
    },
  },
  open: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.2,
      ease: [0, 0, 0.2, 1],
      staggerChildren: 0.05,
      delayChildren: 0.05,
    },
  },
};

// Menu item animation variants
export const MENU_ITEM_VARIANTS: Variants = {
  closed: {
    opacity: 0,
    x: -20,
  },
  open: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.2,
      ease: [0, 0, 0.2, 1],
    },
  },
};

// Icon rotation animation
export const ICON_ROTATE_VARIANTS: Variants = {
  closed: { rotate: 0 },
  open: { rotate: 180 },
};

// Backdrop animation
export const BACKDROP_VARIANTS: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

// Stagger container animation variants
export const STAGGER_CONTAINER_VARIANTS: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.1,
    },
  },
};

// Stagger item animation variants
export const STAGGER_ITEM_VARIANTS: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.4, 0, 0.2, 1],
    },
  },
};
