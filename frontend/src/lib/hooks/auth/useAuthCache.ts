import { useCallback } from 'react';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import type { User, CachedAuthData } from '@/lib/types/auth';

/**
 * Hook for managing authentication cache in sessionStorage
 */
export function useAuthCache() {
  const getCachedAuth = useCallback((): CachedAuthData | null => {
    if (typeof window === 'undefined') return null;

    try {
      const cached = sessionStorage.getItem(config.auth.cacheKey);
      if (!cached) return null;

      const data: CachedAuthData = JSON.parse(cached);
      const age = Date.now() - data.timestamp;

      // Check if cache is still valid (within TTL)
      if (age > config.auth.cacheTTL) {
        sessionStorage.removeItem(config.auth.cacheKey);
        return null;
      }

      return data;
    } catch (error) {
      logger.warn('Failed to read auth cache', { component: 'useAuthCache', error });
      return null;
    }
  }, []);

  const setCachedAuth = useCallback((user: User): void => {
    if (typeof window === 'undefined') return;

    try {
      const data: CachedAuthData = {
        user,
        timestamp: Date.now(),
      };
      sessionStorage.setItem(config.auth.cacheKey, JSON.stringify(data));
      logger.debug('Auth cache updated', { component: 'useAuthCache', userId: user.id });
    } catch (error) {
      logger.warn('Failed to write auth cache', { component: 'useAuthCache', error });
    }
  }, []);

  const clearCachedAuth = useCallback((): void => {
    if (typeof window === 'undefined') return;

    try {
      sessionStorage.removeItem(config.auth.cacheKey);
      logger.debug('Auth cache cleared', { component: 'useAuthCache' });
    } catch (error) {
      logger.warn('Failed to clear auth cache', { component: 'useAuthCache', error });
    }
  }, []);

  return {
    getCachedAuth,
    setCachedAuth,
    clearCachedAuth,
  };
}
