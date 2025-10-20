'use client';

import { createContext, ReactNode, useContext, useEffect, useRef, useState } from 'react';
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

type AuthStatus =
  | 'initializing' // First mount, checking cookies
  | 'optimistic' // Cookie found, rendering optimistically while verifying
  | 'authenticated' // Backend has confirmed session
  | 'unauthenticated' // No session or session invalid
  | 'error';

interface AuthContextType {
  user: User | null;
  isLoading: boolean; // Backwards-compat: true only during 'initializing'
  isAuthenticated: boolean; // true for 'optimistic' | 'authenticated'
  status: AuthStatus;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  revalidate: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

const AUTH_CACHE_KEY = config.auth.cacheKey;
const CACHE_TTL_MS = config.auth.cacheTTL;

interface CachedAuth {
  user: User;
  timestamp: number;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const abortControllerRef = useRef<AbortController | null>(null);
  const verifyTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const isLoading = status === 'initializing';
  const isAuthenticated = status === 'optimistic' || status === 'authenticated';

  const getAuthCache = (): CachedAuth | null => {
    try {
      const cached = sessionStorage.getItem(AUTH_CACHE_KEY);
      if (!cached) return null;
      const data: CachedAuth = JSON.parse(cached);
      const age = Date.now() - data.timestamp;
      if (age > CACHE_TTL_MS) {
        sessionStorage.removeItem(AUTH_CACHE_KEY);
        return null;
      }
      return data;
    } catch {
      return null;
    }
  };

  const setAuthCache = (user: User) => {
    try {
      const data: CachedAuth = { user, timestamp: Date.now() };
      sessionStorage.setItem(AUTH_CACHE_KEY, JSON.stringify(data));
    } catch (err) {
      logger.warn('Failed to cache user data', { component: 'AuthContext', err });
    }
  };

  const clearAuthCache = () => {
    try {
      sessionStorage.removeItem(AUTH_CACHE_KEY);
    } catch {}
  };

  const handleInvalidSession = () => {
    setUser(null);
    clearAuthCache();
    setStatus('unauthenticated');
    window.dispatchEvent(new CustomEvent('auth-expired'));
  };

  const verifySession = async (retryCount = 0) => {
    // Abort any in-flight verification
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const backendUrl = config.api.baseUrl;
      const response = await fetch(`${backendUrl}/api/auth/verify`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthCookies(),
        },
        credentials: 'include',
        signal: abortControllerRef.current.signal,
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user) {
          logger.info('Auth verification successful', { component: 'AuthContext', display_name: data.user.display_name });
          setUser(data.user);
          setAuthCache(data.user);
          setStatus('authenticated');
          // Notify listeners that auth has been validated
          window.dispatchEvent(new CustomEvent('auth-validated'));
        } else {
          logger.info('Auth verification returned no user', { component: 'AuthContext' });
          handleInvalidSession();
        }
      } else if (response.status === 401) {
        logger.warn('Auth verification 401 - unauthorized', { component: 'AuthContext' });
        handleInvalidSession();
      } else {
        // Server error - retry once with small backoff
        if (retryCount === 0) {
          await new Promise((r) => setTimeout(r, 300));
          return verifySession(1);
        }
        logger.error('Auth verification failed, staying optimistic', undefined, { component: 'AuthContext', status: response.status });
        // Stay optimistic on persistent server errors
        setStatus('optimistic');
      }
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        logger.debug('Auth verification aborted', { component: 'AuthContext' });
        return;
      }
      logger.error('Auth verification error', error, { component: 'AuthContext' });
      if (retryCount === 0) {
        await new Promise((r) => setTimeout(r, 300));
        return verifySession(1);
      }
      // Stay optimistic on network/offline errors
      setStatus('optimistic');
    }
  };

  const revalidate = async () => {
    const sessionToken = getCookie(config.auth.sessionCookieName);
    if (sessionToken) {
      // Move into optimistic state during validation
      if (status === 'unauthenticated' || status === 'initializing') {
        setStatus('optimistic');
      }
      await verifySession();
    }
  };

  const login = async (accessToken: string, refreshToken: string) => {
    try {
      const backendUrl = config.api.baseUrl;
      const response = await fetch(`${backendUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          access_token: accessToken,
          refresh_token: refreshToken,
          token_expires_at: Date.now() + 3600 * 1000,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
      }

      // After login, verify in background
      setStatus('optimistic');
      await verifySession();
    } catch (error) {
      logger.error('Authentication error', error as Error, { component: 'AuthContext' });
      throw error;
    }
  };

  const logout = async () => {
    try {
      const backendUrl = config.api.baseUrl;
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
      } else {
        logger.info('Backend logout successful', { component: 'AuthContext' });
      }
    } catch (error) {
      logger.error('Logout error', error as Error, { component: 'AuthContext' });
    } finally {
      setUser(null);
      clearAuthCache();
      setStatus('unauthenticated');
      // Dispatch logout event to notify other contexts (like workflow context)
      window.dispatchEvent(new Event('auth-logout'));
    }
  };

  const refreshUser = async () => {
    await revalidate();
  };

  // Initialize from cookie and cache
  useEffect(() => {
    const sessionToken = getCookie(config.auth.sessionCookieName);

    if (!sessionToken) {
      setUser(null);
      setStatus('unauthenticated');
      return;
    }

    // Try to load from session storage cache
    const cached = getAuthCache();
    if (cached) {
      logger.debug('Using cached user data', { component: 'AuthContext' });
      setUser(cached.user);
      setStatus('optimistic');
    } else {
      setStatus('optimistic');
    }

    // Schedule background verification (non-blocking)
    verifyTimeoutRef.current = setTimeout(() => {
      verifySession().catch((err) => logger.error('Verify session error', err as Error, { component: 'AuthContext' }));
    }, 100);

    return () => {
      if (verifyTimeoutRef.current) clearTimeout(verifyTimeoutRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  // Listen for auth update events (from callback page)
  useEffect(() => {
    const handleAuthUpdate = () => {
      revalidate();
    };

    window.addEventListener('auth-update', handleAuthUpdate);
    return () => {
      window.removeEventListener('auth-update', handleAuthUpdate);
    };
  }, [status]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    status,
    login,
    logout,
    refreshUser,
    revalidate,
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
