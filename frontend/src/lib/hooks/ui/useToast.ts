import { TIMING } from '@/lib/constants';
import { useCallback } from 'react';
import { toast as sonnerToast } from 'sonner';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastOptions {
  description?: string;
  duration?: number;
}

/**
 * Unified toast helper built on top of `sonner` that enforces
 * consistent defaults and copy style across the app.
 */
export function useToast() {
  const defaultDuration = TIMING.TOAST_DURATION;

  const success = useCallback((message: string, options?: ToastOptions) => {
    return sonnerToast.success(message, {
      duration: options?.duration ?? defaultDuration,
      description: options?.description,
    });
  }, [defaultDuration]);

  const error = useCallback((message: string, options?: ToastOptions) => {
    return sonnerToast.error(message, {
      duration: options?.duration ?? defaultDuration,
      description: options?.description,
    });
  }, [defaultDuration]);

  const warning = useCallback((message: string, options?: ToastOptions) => {
    return sonnerToast.warning(message, {
      duration: options?.duration ?? defaultDuration,
      description: options?.description,
    });
  }, [defaultDuration]);

  const info = useCallback((message: string, options?: ToastOptions) => {
    return sonnerToast.info(message, {
      duration: options?.duration ?? defaultDuration,
      description: options?.description,
    });
  }, [defaultDuration]);

  return { success, error, warning, info };
}
