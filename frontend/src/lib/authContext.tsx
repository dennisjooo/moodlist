'use client';

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { getAuthCookies, getCookie } from './cookies';

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
          console.log('Auth check successful, user found:', data.user.display_name);
          setUser(data.user);
        } else {
          console.log('Auth check successful, no user found');
          setUser(null);
        }
      } else if (response.status === 401) {
        console.log('Auth check failed with 401 - unauthorized');
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
      console.error('Auth check failed:', error);
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
      // Refresh user data
      await checkAuthStatus();
    } catch (error) {
      console.error('Authentication error:', error);
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