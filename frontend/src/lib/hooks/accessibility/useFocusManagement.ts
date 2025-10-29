'use client';

import { useCallback, useRef } from 'react';

/**
 * Hook for managing focus within a component
 * Provides utilities for trapping focus, moving focus, and restoring focus
 */
export function useFocusManagement() {
    const previousFocusRef = useRef<HTMLElement | null>(null);

    const saveCurrentFocus = useCallback(() => {
        previousFocusRef.current = document.activeElement as HTMLElement;
    }, []);

    const restoreFocus = useCallback(() => {
        if (previousFocusRef.current && document.contains(previousFocusRef.current)) {
            previousFocusRef.current.focus();
        }
    }, []);

    const focusFirstFocusable = useCallback((container: HTMLElement) => {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstFocusable = focusableElements[0] as HTMLElement;
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }, []);

    const focusLastFocusable = useCallback((container: HTMLElement) => {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement;
        if (lastFocusable) {
            lastFocusable.focus();
        }
    }, []);

    const trapFocus = useCallback((container: HTMLElement) => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key !== 'Tab') return;

            const focusableElements = container.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );

            const firstFocusable = focusableElements[0] as HTMLElement;
            const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement;

            if (event.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstFocusable) {
                    event.preventDefault();
                    lastFocusable?.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastFocusable) {
                    event.preventDefault();
                    firstFocusable?.focus();
                }
            }
        };

        container.addEventListener('keydown', handleKeyDown);
        return () => container.removeEventListener('keydown', handleKeyDown);
    }, []);

    return {
        saveCurrentFocus,
        restoreFocus,
        focusFirstFocusable,
        focusLastFocusable,
        trapFocus,
    };
}
