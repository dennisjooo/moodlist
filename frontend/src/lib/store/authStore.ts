import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import apiClient from '@/lib/axios';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import type { User, CachedAuthData } from '@/lib/types/auth';
import { getAuthCookies, getCookie } from '../cookies';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isValidated: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  checkAuthStatus: (retryCount?: number, skipCache?: boolean) => Promise<void>;
}

function isUserDifferent(user1: User | null, user2: User | null): boolean {
  if (user1 === null && user2 === null) return false;
  if (user1 === null || user2 === null) return true;

  return user1.id !== user2.id ||
    user1.display_name !== user2.display_name ||
    user1.email !== user2.email ||
    user1.profile_image_url !== user2.profile_image_url;
}

function getCachedAuth(): CachedAuthData | null {
  if (typeof window === 'undefined') return null;

  try {
    const cached = sessionStorage.getItem(config.auth.cacheKey);
    if (!cached) return null;

    const data: CachedAuthData = JSON.parse(cached);
    const age = Date.now() - data.timestamp;

    if (age > config.auth.cacheTTL) {
      sessionStorage.removeItem(config.auth.cacheKey);
      return null;
    }

    return data;
  } catch (error) {
    logger.warn('Failed to read auth cache', { component: 'authStore', error });
    return null;
  }
}

function setCachedAuth(user: User): void {
  if (typeof window === 'undefined') return;

  try {
    const data: CachedAuthData = {
      user,
      timestamp: Date.now(),
    };
    sessionStorage.setItem(config.auth.cacheKey, JSON.stringify(data));
    logger.debug('Auth cache updated', { component: 'authStore', userId: user.id });
  } catch (error) {
    logger.warn('Failed to write auth cache', { component: 'authStore', error });
  }
}

function clearCachedAuth(): void {
  if (typeof window === 'undefined') return;

  try {
    sessionStorage.removeItem(config.auth.cacheKey);
    logger.debug('Auth cache cleared', { component: 'authStore' });
  } catch (error) {
    logger.warn('Failed to clear auth cache', { component: 'authStore', error });
  }
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isValidated: false,

      checkAuthStatus: async (retryCount = 0, skipCache = false) => {
        try {
          const currentUser = get().user;

          // Check cache first (unless explicitly skipped)
          if (!skipCache && retryCount === 0) {
            const cached = getCachedAuth();
            if (cached) {
              logger.debug('Using cached auth data', { component: 'authStore', display_name: cached.user.display_name });
              set({
                user: cached.user,
                isAuthenticated: true,
                isValidated: false,
              });

              // Start background validation
              setTimeout(() => get().checkAuthStatus(0, true), 0);
              return;
            }
          }

          // Only show loading if we're making an actual request and no user is set yet
          if (retryCount === 0 && !currentUser) {
            set({ isLoading: true });
          }

          // Fetch user info from backend
          const response = await apiClient.get<{ user: User }>('/api/auth/verify', {
            headers: {
              ...getAuthCookies(),
            },
          });

          if (response.data.user) {
            logger.info('Auth verification successful', { component: 'authStore', display_name: response.data.user.display_name });

            // Only update state if user data actually changed
            if (isUserDifferent(currentUser, response.data.user)) {
              logger.debug('User data changed, updating state', { component: 'authStore' });
              set({
                user: response.data.user,
                isAuthenticated: true,
                isValidated: true,
                isLoading: false,
              });
            } else {
              logger.debug('User data unchanged, skipping re-render', { component: 'authStore' });
              set({
                isValidated: true,
                isLoading: false,
              });
            }

            setCachedAuth(response.data.user);

            // Emit validated event
            if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('auth-validated', { detail: { user: response.data.user } }));
            }
          } else {
            logger.info('Auth verification - no user', { component: 'authStore' });
            set({
              user: null,
              isAuthenticated: false,
              isValidated: true,
              isLoading: false,
            });
            clearCachedAuth();
          }
        } catch (error: unknown) {
          const axiosError = error as { response?: { status?: number } };
          if (axiosError.response?.status === 401) {
            logger.warn('Auth verification failed - unauthorized', { component: 'authStore' });
            set({
              user: null,
              isAuthenticated: false,
              isValidated: true,
              isLoading: false,
            });
            clearCachedAuth();

            // Emit expired event if we had a user before
            if (get().user && typeof window !== 'undefined') {
              window.dispatchEvent(new Event('auth-expired'));
            }
          } else {
            // Other error - if it's our first attempt, try again after a short delay
            if (retryCount === 0) {
              await new Promise(resolve => setTimeout(resolve, 200));
              return get().checkAuthStatus(1, skipCache);
            }
            logger.error('Auth verification error', error, { component: 'authStore' });
            set({
              user: null,
              isAuthenticated: false,
              isValidated: true,
              isLoading: false,
            });
            clearCachedAuth();
          }
        }
      },

      login: async (accessToken: string, refreshToken: string) => {
        try {
          await apiClient.post('/api/auth/login', {
            access_token: accessToken,
            refresh_token: refreshToken,
            token_expires_at: Date.now() + (3600 * 1000),
          });

          // Session cookie is now set by backend
          // Refresh user data
          await get().checkAuthStatus();
        } catch (error) {
          logger.error('Authentication error', error, { component: 'authStore' });
          throw error;
        }
      },

      logout: async () => {
        // Immediately clear local state for optimistic UX
        set({
          user: null,
          isAuthenticated: false,
          isValidated: false,
        });
        clearCachedAuth();

        // Dispatch logout event to notify other contexts (like workflow context)
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('auth-logout'));
        }

        // Make backend logout call in background (fire and forget)
        try {
          apiClient.post('/api/auth/logout', {}, {
            headers: {
              ...getAuthCookies(),
            },
          }).then(() => {
            logger.info('Backend logout successful', { component: 'authStore' });
          }).catch((error) => {
            logger.error('Backend logout failed', error, { component: 'authStore' });
          });
        } catch (error) {
          logger.error('Logout setup error', error, { component: 'authStore' });
        }
      },

      refreshUser: async () => {
        await get().checkAuthStatus();
      },
    }),
    { name: 'AuthStore' }
  )
);

// Initialize auth store on client side
if (typeof window !== 'undefined') {
  // Optimistic auth: Check for session cookie immediately
  const sessionCookie = getCookie(config.auth.sessionCookieName);

  if (sessionCookie) {
    // We have a session cookie - set optimistic authenticated state
    // Check cache first for instant user data
    const cached = getCachedAuth();
    if (cached) {
      logger.debug('Optimistic auth: Using cached user data', { component: 'authStore' });
      useAuthStore.setState({
        user: cached.user,
        isAuthenticated: true,
        isValidated: false,
      });
    } else {
      logger.debug('Optimistic auth: Cookie present, will verify', { component: 'authStore' });
    }
  }

  // Always verify with backend (will use cache if available)
  useAuthStore.getState().checkAuthStatus();

  // Listen for auth update events (from callback page)
  const handleAuthUpdate = () => {
    clearCachedAuth();
    useAuthStore.getState().checkAuthStatus(0, true);
  };

  window.addEventListener('auth-update', handleAuthUpdate);
}
