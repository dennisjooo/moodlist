'use client';

import { useAuth } from '@/lib/contexts/AuthContext';
import { useCallback, useState } from 'react';

/**
 * Custom hook for protecting actions behind authentication
 * 
 * Usage:
 * ```tsx
 * const { requireAuth, showLoginDialog, LoginDialog } = useAuthGuard();
 * 
 * const handleSubmit = requireAuth(async (mood: string) => {
 *   await startWorkflow(mood);
 * });
 * 
 * return (
 *   <>
 *     <button onClick={() => handleSubmit('happy')}>Create</button>
 *     <LoginDialog />
 *   </>
 * );
 * ```
 */
export function useAuthGuard() {
  const { isAuthenticated } = useAuth();
  const [showLoginDialog, setShowLoginDialog] = useState(false);

  /**
   * Wraps a callback to require authentication before execution
   * If user is not authenticated, shows login dialog instead
   */
  const requireAuth = useCallback(<T extends unknown[]>(
    callback: (...args: T) => void | Promise<void>
  ) => {
    return (...args: T) => {
      if (!isAuthenticated) {
        setShowLoginDialog(true);
        return;
      }
      return callback(...args);
    };
  }, [isAuthenticated]);

  /**
   * Check if user is authenticated (without wrapping a callback)
   */
  const checkAuth = useCallback((): boolean => {
    if (!isAuthenticated) {
      setShowLoginDialog(true);
      return false;
    }
    return true;
  }, [isAuthenticated]);

  return {
    requireAuth,
    checkAuth,
    showLoginDialog,
    setShowLoginDialog,
    isAuthenticated,
  };
}

