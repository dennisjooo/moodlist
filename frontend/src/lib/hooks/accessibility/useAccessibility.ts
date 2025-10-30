'use client';

import { useEffect, useRef } from 'react';
import { announceToScreenReader, trapFocus, focusManagement } from '@/lib/utils/accessibility';

/**
 * Hook to announce messages to screen readers
 */
export function useScreenReaderAnnouncement() {
  return {
    announce: (message: string, priority: 'polite' | 'assertive' = 'polite') => {
      announceToScreenReader(message, priority);
    },
  };
}

/**
 * Hook to trap focus within a container (for modals/dialogs)
 */
export function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const cleanup = trapFocus(containerRef.current);
    return cleanup;
  }, [isActive]);

  return containerRef;
}

/**
 * Hook to restore focus when a component unmounts
 */
export function useRestoreFocus() {
  const restoreFocusRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // Save focus on mount
    restoreFocusRef.current = focusManagement.saveFocus();

    // Restore focus on unmount
    return () => {
      restoreFocusRef.current?.();
    };
  }, []);
}

/**
 * Hook to manage skip links for keyboard navigation
 */
export function useSkipLink(targetId: string) {
  const handleSkip = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return { handleSkip };
}

/**
 * Hook to detect if user prefers reduced motion
 */
export function useReducedMotion() {
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion.current = mediaQuery.matches;

    const handleChange = (e: MediaQueryListEvent) => {
      prefersReducedMotion.current = e.matches;
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion.current;
}

/**
 * Hook for keyboard navigation in lists
 */
export function useListKeyboardNavigation<T extends HTMLElement>(
  itemCount: number,
  onSelect?: (index: number) => void
) {
  const currentIndexRef = useRef(0);
  const listRef = useRef<T>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    let newIndex = currentIndexRef.current;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        newIndex = Math.min(currentIndexRef.current + 1, itemCount - 1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        newIndex = Math.max(currentIndexRef.current - 1, 0);
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = itemCount - 1;
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (onSelect) {
          onSelect(currentIndexRef.current);
        }
        return;
    }

    if (newIndex !== currentIndexRef.current) {
      currentIndexRef.current = newIndex;
      // Focus the item at the new index
      const items = listRef.current?.querySelectorAll('[role="option"], [role="menuitem"]');
      const item = items?.[newIndex] as HTMLElement;
      item?.focus();
    }
  };

  return { listRef, handleKeyDown };
}

