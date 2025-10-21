'use client';

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { getAuthCookies, getCookie } from '../cookies';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

export interface User {
  id: number;
  spotify_id: string;
  email?: string;
  display_name: string;
  profile_image_url?: string;
  is_active: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isValidated: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

interface CachedAuthData {
  user: User;
  timestamp: number;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Track if backend verification completed
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isValidated, setIsValidated] = useState(false);

  // Get cached auth data from SessionStorage
  const getCachedAuth = (): CachedAuthData | null => {
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
      logger.warn('Failed to read auth cache', { component: 'AuthContext', error });
      return null;
    }
  };

  // Set cached auth data in SessionStorage
  const setCachedAuth = (user: User) => {
    if (typeof window === 'undefined') return;
    try {
      const data: CachedAuthData = {
        user,
        timestamp: Date.now(),
      };
      sessionStorage.setItem(config.auth.cacheKey, JSON.stringify(data));
    } catch (error) {
      logger.warn('Failed to write auth cache', { component: 'AuthContext', error });
    }
  };

  // Clear cached auth data
  const clearCachedAuth = () => {
    if (typeof window === 'undefined') return;
    try {
      sessionStorage.removeItem(config.auth.cacheKey);
    } catch (error) {
      logger.warn('Failed to clear auth cache', { component: 'AuthContext', error });
    }
  };

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
          setUser(data.user);
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
    try {
      const backendUrl = config.api.baseUrl;

      // Call backend logout to clear session
      const response = await fetch(`${backendUrl}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthCookies(),
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error('Backend logout failed', undefined, { component: 'AuthContext', status: response.status, errorText });
        // Don't throw error - still clear local state for better UX
      } else {
        logger.info('Backend logout successful', { component: 'AuthContext' });
      }
    } catch (error) {
      logger.error('Logout error', error, { component: 'AuthContext' });
      // Don't throw error - still clear local state for better UX
    } finally {
      // Always clear local state after attempting backend logout
      setUser(null);
      setIsValidated(false);
      clearCachedAuth();

      // Dispatch logout event to notify other contexts (like workflow context)
      window.dispatchEvent(new Event('auth-logout'));
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
    isValidated: Boolean(user),
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