'use client';

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { getAuthCookies, getCookie } from './cookies';
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
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const checkAuthStatus = async (retryCount = 0) => {
    try {
      // Only show loading if we're making an actual request
      if (retryCount === 0) {
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
          logger.info('Auth check successful, user found', { component: 'AuthContext', display_name: data.user.display_name });
          setUser(data.user);
        } else {
          logger.info('Auth check successful, no user found', { component: 'AuthContext' });
          setUser(null);
        }
      } else if (response.status === 401) {
        logger.warn('Auth check failed with 401 - unauthorized', { component: 'AuthContext' });
        setUser(null);
      } else {
        // Other error - if it's our first attempt, try again after a short delay
        if (retryCount === 0) {
          await new Promise(resolve => setTimeout(resolve, 200));
          return checkAuthStatus(1);
        }
        setUser(null);
      }
    } catch (error) {
      logger.error('Auth check failed', error, { component: 'AuthContext' });
      // If it's our first attempt and we get a network error, try again
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 200));
        return checkAuthStatus(1);
      }
      setUser(null);
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

      // Dispatch logout event to notify other contexts (like workflow context)
      window.dispatchEvent(new Event('auth-logout'));
    }
  };

  const refreshUser = async () => {
    await checkAuthStatus();
  };

  useEffect(() => {
    // Always check auth status on mount to ensure we have the latest state
    checkAuthStatus();

    // Listen for auth update events (from callback page)
    const handleAuthUpdate = () => {
      checkAuthStatus();
    };

    window.addEventListener('auth-update', handleAuthUpdate);

    return () => {
      window.removeEventListener('auth-update', handleAuthUpdate);
    };
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: Boolean(user),
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