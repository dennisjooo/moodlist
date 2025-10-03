'use client';

import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { getAuthCookies } from './cookies';

export interface User {
  id: number;
  spotify_id: string;
  email?: string;
  display_name: string;
  profile_image_url?: string;
  is_active: boolean;
  created_at: string;
}

interface CachedAuthState {
  user: User | null;
  timestamp: number;
  expiresAt: number;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  getAuthMetrics: () => AuthMetrics;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth cache configuration
const AUTH_CACHE_KEY = 'auth_state';
const AUTH_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const AUTH_CACHE_CHECK_INTERVAL = 30 * 1000; // Check cache every 30 seconds
const TOKEN_REFRESH_THRESHOLD = 10 * 60 * 1000; // Refresh token 10 minutes before expiry

// Performance monitoring
interface AuthMetrics {
  totalCalls: number;
  cacheHits: number;
  cacheMisses: number;
  averageResponseTime: number;
  lastCallTime: number;
  errors: number;
}

const AUTH_METRICS_KEY = 'auth_metrics';

const getAuthMetrics = (): AuthMetrics => {
  try {
    const stored = localStorage.getItem(AUTH_METRICS_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Error reading auth metrics:', error);
  }

  return {
    totalCalls: 0,
    cacheHits: 0,
    cacheMisses: 0,
    averageResponseTime: 0,
    lastCallTime: 0,
    errors: 0,
  };
};

const updateAuthMetrics = (metrics: Partial<AuthMetrics>): void => {
  try {
    const current = getAuthMetrics();
    const updated = { ...current, ...metrics };
    localStorage.setItem(AUTH_METRICS_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Error updating auth metrics:', error);
  }
};

const recordAuthCall = (isCacheHit: boolean, responseTime: number, isError = false): void => {
  const metrics = getAuthMetrics();
  metrics.totalCalls++;
  metrics.lastCallTime = Date.now();

  if (isCacheHit) {
    metrics.cacheHits++;
  } else {
    metrics.cacheMisses++;
  }

  if (isError) {
    metrics.errors++;
  }

  // Update average response time (simple moving average)
  metrics.averageResponseTime = (metrics.averageResponseTime + responseTime) / 2;

  updateAuthMetrics(metrics);
};

// Cache management utilities
const getCachedAuthState = (): CachedAuthState | null => {
  try {
    const cached = sessionStorage.getItem(AUTH_CACHE_KEY);
    if (!cached) return null;

    const parsedCache: CachedAuthState = JSON.parse(cached);
    const now = Date.now();

    // Check if cache is expired
    if (now > parsedCache.expiresAt) {
      sessionStorage.removeItem(AUTH_CACHE_KEY);
      return null;
    }

    return parsedCache;
  } catch (error) {
    console.error('Error reading auth cache:', error);
    sessionStorage.removeItem(AUTH_CACHE_KEY);
    return null;
  }
};

const setCachedAuthState = (user: User | null): void => {
  try {
    const cacheData: CachedAuthState = {
      user,
      timestamp: Date.now(),
      expiresAt: Date.now() + AUTH_CACHE_TTL,
    };
    sessionStorage.setItem(AUTH_CACHE_KEY, JSON.stringify(cacheData));
  } catch (error) {
    console.error('Error setting auth cache:', error);
  }
};

const clearCachedAuthState = (): void => {
  try {
    sessionStorage.removeItem(AUTH_CACHE_KEY);
  } catch (error) {
    console.error('Error clearing auth cache:', error);
  }
};

const refreshAccessToken = async (): Promise<boolean> => {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
    const cookies = getAuthCookies();

    const response = await fetch(`${backendUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...cookies,
      },
      credentials: 'include',
    });

    if (response.ok) {
      console.log('Token refresh successful');
      return true;
    } else {
      console.error('Token refresh failed:', response.status);
      return false;
    }
  } catch (error) {
    console.error('Token refresh error:', error);
    return false;
  }
};

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const verificationInProgress = useRef(false);
  const lastVerificationTime = useRef<number>(0);

  // Minimum time between auth verifications (30 seconds)
  const MIN_VERIFICATION_INTERVAL = 30 * 1000;

  const verifyAuthWithBackend = async (retryCount = 0): Promise<User | null> => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
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
          console.log('Auth verification successful:', data.user.display_name);
          return data.user;
        } else {
          console.log('Auth verification successful, no user found');
          return null;
        }
      } else if (response.status === 401) {
        console.log('Auth verification failed with 401 - unauthorized');
        return null;
      } else {
        // Other error - if it's our first attempt, try again after a short delay
        if (retryCount === 0) {
          await new Promise(resolve => setTimeout(resolve, 200));
          return verifyAuthWithBackend(1);
        }
        return null;
      }
    } catch (error) {
      console.error('Auth verification failed:', error);
      // If it's our first attempt and we get a network error, try again
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 200));
        return verifyAuthWithBackend(1);
      }
      return null;
    }
  };

  const checkAuthStatus = useCallback(async (force = false): Promise<void> => {
    const startTime = Date.now();

    // Prevent concurrent verification requests
    if (verificationInProgress.current) {
      console.log('Auth verification already in progress, skipping');
      recordAuthCall(false, Date.now() - startTime);
      return;
    }

    // Check if we need to verify (not too frequent and not forced)
    const now = Date.now();
    if (!force && (now - lastVerificationTime.current) < MIN_VERIFICATION_INTERVAL) {
      console.log('Auth verification too recent, skipping');
      recordAuthCall(false, Date.now() - startTime);
      return;
    }

    // Check cache first unless forced
    if (!force) {
      const cachedState = getCachedAuthState();
      if (cachedState) {
        console.log('Using cached auth state');
        setUser(cachedState.user);
        recordAuthCall(true, Date.now() - startTime);
        return;
      }
    }

    verificationInProgress.current = true;
    lastVerificationTime.current = now;

    let isError = false;
    try {
      setIsLoading(true);

      // Try to refresh token proactively if needed
      await attemptProactiveTokenRefresh();

      const verifiedUser = await verifyAuthWithBackend();
      setUser(verifiedUser);

      // Cache the result
      setCachedAuthState(verifiedUser);

    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
      clearCachedAuthState();
      isError = true;
    } finally {
      setIsLoading(false);
      verificationInProgress.current = false;

      // Record metrics
      recordAuthCall(false, Date.now() - startTime, isError);
    }
  }, []);

  const attemptProactiveTokenRefresh = async (): Promise<void> => {
    try {
      // Try to refresh the token proactively
      // This helps avoid auth failures during active sessions
      const refreshSuccess = await refreshAccessToken();
      if (refreshSuccess) {
        console.log('Proactive token refresh successful');
      }
    } catch (error) {
      // Token refresh failed, but don't block auth verification
      console.log('Proactive token refresh failed, continuing with auth verification');
    }
  };

  const login = async (accessToken: string, refreshToken: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

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
      // Force refresh user data and cache
      await checkAuthStatus(true);

      // Dispatch login event to notify other contexts
      window.dispatchEvent(new Event('auth-login'));
    } catch (error) {
      console.error('Authentication error:', error);
      // Clear any cached state on login failure
      clearCachedAuthState();
      throw error;
    }
  };

  const logout = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

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
        console.error('Backend logout failed:', response.status, errorText);
        // Don't throw error - still clear local state for better UX
      } else {
        console.log('Backend logout successful');
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Don't throw error - still clear local state for better UX
    } finally {
      // Always clear local state and cache after attempting backend logout
      setUser(null);
      clearCachedAuthState();

      // Dispatch logout event to notify other contexts (like workflow context)
      window.dispatchEvent(new Event('auth-logout'));
    }
  };

  const refreshUser = async () => {
    await checkAuthStatus(true); // Force refresh
  };

  const getAuthMetrics = (): AuthMetrics => {
    return getAuthMetrics();
  };

  useEffect(() => {
    // Check auth status on mount, but prefer cached state
    checkAuthStatus();

    // Set up periodic cache validation
    const cacheCheckInterval = setInterval(() => {
      const cachedState = getCachedAuthState();
      if (cachedState && Date.now() > cachedState.expiresAt) {
        console.log('Auth cache expired, refreshing...');
        checkAuthStatus(true);
      }
    }, AUTH_CACHE_CHECK_INTERVAL);

    // Set up periodic token refresh check (every 5 minutes)
    const tokenRefreshInterval = setInterval(async () => {
      try {
        await attemptProactiveTokenRefresh();
      } catch (error) {
        console.error('Periodic token refresh failed:', error);
      }
    }, 5 * 60 * 1000); // Check every 5 minutes

    // Listen for auth update events (from callback page)
    const handleAuthUpdate = () => {
      console.log('Auth update event received, refreshing...');
      checkAuthStatus(true);
    };

    // Listen for login events
    const handleAuthLogin = () => {
      console.log('Auth login event received, refreshing...');
      checkAuthStatus(true);
    };

    // Cross-tab synchronization using localStorage events
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === AUTH_CACHE_KEY && e.newValue) {
        try {
          const newCache = JSON.parse(e.newValue);
          if (newCache && Date.now() <= newCache.expiresAt) {
            console.log('Auth state updated from another tab');
            setUser(newCache.user);
          }
        } catch (error) {
          console.error('Error parsing auth state from storage event:', error);
        }
      }
    };

    window.addEventListener('auth-update', handleAuthUpdate);
    window.addEventListener('auth-login', handleAuthLogin);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      clearInterval(cacheCheckInterval);
      clearInterval(tokenRefreshInterval);
      window.removeEventListener('auth-update', handleAuthUpdate);
      window.removeEventListener('auth-login', handleAuthLogin);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [checkAuthStatus]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
    login,
    logout,
    refreshUser,
    getAuthMetrics,
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