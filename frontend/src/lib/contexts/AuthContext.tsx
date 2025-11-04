'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { getAuthCookies, getCookie } from '../cookies';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import { User, AuthContextType, AuthProviderProps } from '../types/auth';
import { useAuthCache } from '@/lib/hooks/auth/useAuthCache';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to compare user objects and check if they're meaningfully different
function isUserDifferent(user1: User | null, user2: User | null): boolean {
  if (user1 === null && user2 === null) return false;
  if (user1 === null || user2 === null) return true;

  // Compare key properties that would affect UI
  return user1.id !== user2.id ||
    user1.display_name !== user2.display_name ||
    user1.email !== user2.email ||
    user1.profile_image_url !== user2.profile_image_url;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Track if backend verification completed
  const [isValidated, setIsValidated] = useState(false);

  // Use the extracted cache hook
  const { getCachedAuth, setCachedAuth, clearCachedAuth } = useAuthCache();

  const checkAuthStatus = async (retryCount = 0, skipCache = false) => {
    try {
      // Check cache first (unless explicitly skipped)
      if (!skipCache && retryCount === 0) {
        const cached = getCachedAuth();
        if (cached) {
          logger.debug('Using cached auth data', { component: 'AuthContext', display_name: cached.user.display_name });
          setUser(cached.user);
          setIsValidated(false); // Not validated yet, will validate in background

          // Start background validation
          setTimeout(() => checkAuthStatus(0, true), 0);
          return;
        }
      }

      // Only show loading if we're making an actual request and no user is set yet
      if (retryCount === 0 && !user) {
        setIsLoading(true);
      }

      // Fetch user info from backend
      const backendUrl = config.api.baseUrl;
      const cookies = getAuthCookies();

      const response = await fetch(`${backendUrl}/api/auth/verify`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...cookies,
        },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user) {
          logger.info('Auth verification successful', { component: 'AuthContext', display_name: data.user.display_name });

          // Only update state if user data actually changed
          if (isUserDifferent(user, data.user)) {
            logger.debug('User data changed, updating state', { component: 'AuthContext' });
            setUser(data.user);
          } else {
            logger.debug('User data unchanged, skipping re-render', { component: 'AuthContext' });
          }

          setCachedAuth(data.user);
          setIsValidated(true);

          // Emit validated event
          window.dispatchEvent(new CustomEvent('auth-validated', { detail: { user: data.user } }));
        } else {
          logger.info('Auth verification - no user', { component: 'AuthContext' });
          setUser(null);
          clearCachedAuth();
          setIsValidated(true);
        }
      } else if (response.status === 401) {
        logger.warn('Auth verification failed - unauthorized', { component: 'AuthContext' });
        setUser(null);
        clearCachedAuth();
        setIsValidated(true);

        // Emit expired event if we had a user before
        if (user) {
          window.dispatchEvent(new Event('auth-expired'));
        }
      } else {
        // Other error - if it's our first attempt, try again after a short delay
        if (retryCount === 0) {
          await new Promise(resolve => setTimeout(resolve, 200));
          return checkAuthStatus(1, skipCache);
        }
        setUser(null);
        clearCachedAuth();
        setIsValidated(true);
      }
    } catch (error) {
      logger.error('Auth verification error', error, { component: 'AuthContext' });
      // If it's our first attempt and we get a network error, try again
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 200));
        return checkAuthStatus(1, skipCache);
      }
      setUser(null);
      clearCachedAuth();
      setIsValidated(true);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (accessToken: string, refreshToken: string) => {
    try {
      const backendUrl = config.api.baseUrl;

      // Send tokens to backend for user creation/session
      const response = await fetch(`${backendUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          access_token: accessToken,
          refresh_token: refreshToken,
          token_expires_at: Date.now() + (3600 * 1000), // Default 1 hour expiry
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
      }

      // Session cookie is now set by backend
      // Refresh user data
      await checkAuthStatus();
    } catch (error) {
      logger.error('Authentication error', error, { component: 'AuthContext' });
      throw error;
    }
  };

  const logout = async () => {
    // Immediately clear local state for optimistic UX
    setUser(null);
    setIsValidated(false);
    clearCachedAuth();

    // Dispatch logout event to notify other contexts (like workflow context)
    window.dispatchEvent(new Event('auth-logout'));

    // Make backend logout call in background (fire and forget)
    try {
      const backendUrl = config.api.baseUrl;

      fetch(`${backendUrl}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthCookies(),
        },
        credentials: 'include',
      }).then(async (response) => {
        if (!response.ok) {
          const errorText = await response.text();
          logger.error('Backend logout failed', undefined, { component: 'AuthContext', status: response.status, errorText });
        } else {
          logger.info('Backend logout successful', { component: 'AuthContext' });
        }
      }).catch((error) => {
        logger.error('Logout error', error, { component: 'AuthContext' });
      });
    } catch (error) {
      logger.error('Logout setup error', error, { component: 'AuthContext' });
    }
  };

  const refreshUser = async () => {
    await checkAuthStatus();
  };

  useEffect(() => {
    // Optimistic auth: Check for session cookie immediately
    const sessionCookie = getCookie(config.auth.sessionCookieName);

    if (sessionCookie) {
      // We have a session cookie - set optimistic authenticated state
      // Check cache first for instant user data
      const cached = getCachedAuth();
      if (cached) {
        logger.debug('Optimistic auth: Using cached user data', { component: 'AuthContext' });
        setUser(cached.user);
        setIsValidated(false);
      } else {
        logger.debug('Optimistic auth: Cookie present, will verify', { component: 'AuthContext' });
        // Cookie present but no cache - we'll verify shortly
      }
    }

    // Always verify with backend (will use cache if available)
    checkAuthStatus();

    // Listen for auth update events (from callback page)
    const handleAuthUpdate = () => {
      clearCachedAuth(); // Clear cache to force fresh verification
      checkAuthStatus(0, true);
    };

    window.addEventListener('auth-update', handleAuthUpdate);

    return () => {
      window.removeEventListener('auth-update', handleAuthUpdate);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
    isValidated,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}