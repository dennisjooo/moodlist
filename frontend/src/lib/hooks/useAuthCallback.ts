import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import apiClient from '@/lib/axios';
import { logger } from '@/lib/utils/logger';

export type AuthStatus = 'loading' | 'success' | 'error';
export type AuthErrorType = 'whitelist' | 'generic' | null;

export interface AuthCallbackState {
  status: AuthStatus;
  errorMessage: string;
  errorType: AuthErrorType;
  currentStage: number;
  redirectPath: string | null;
  redirectLabel: string;
}

function deriveRedirectLabel(path: string | null) {
  if (!path || path === "/") {
    return "our homepage";
  }

  try {
    const base =
      typeof window !== "undefined" ? window.location.origin : "https://moodlist.app";
    const url = new URL(path, base);
    if (!url.pathname || url.pathname === "/") {
      return "our homepage";
    }
    return url.pathname;
  } catch {
    return path;
  }
}

export function useAuthCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [errorType, setErrorType] = useState<AuthErrorType>(null);
  const [currentStage, setCurrentStage] = useState(0);
  const [redirectPath, setRedirectPath] = useState<string | null>(null);

  const redirectLabel = useMemo(
    () => deriveRedirectLabel(redirectPath),
    [redirectPath]
  );

  useEffect(() => {
    const handleCallback = async () => {
      setStatus('loading');
      setErrorMessage('');
      setErrorType(null);
      setCurrentStage(0);

      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Validate state parameter for security
      const storedState = sessionStorage.getItem('spotify_auth_state');
      if (state !== storedState) {
        setStatus('error');
        setErrorMessage('Security validation failed');
        sessionStorage.removeItem('spotify_auth_state');
        return;
      }
      sessionStorage.removeItem('spotify_auth_state');

      if (error) {
        setStatus('error');
        setErrorMessage(error === 'access_denied' ? 'Access denied by user' : 'Authentication failed');
        return;
      }

      if (!code) {
        setStatus('error');
        setErrorMessage('No authorization code received');
        return;
      }

      try {
        // Exchange code for tokens using backend
        setCurrentStage(1);
        const tokenResponse = await apiClient.post<{ access_token: string; refresh_token: string; expires_in: number }>(`/api/spotify/token`, null, {
          params: { code },
        });

        const tokenData = tokenResponse.data;

        // Use new authentication system
        try {
          // Begin finalizing session
          // Register/Login through backend API (this will set session cookies)
          await apiClient.post('/api/auth/login', {
            access_token: tokenData.access_token,
            refresh_token: tokenData.refresh_token,
            token_expires_at: Date.now() + (tokenData.expires_in * 1000),
          });

          setCurrentStage(2);

          // Add a small delay to ensure cookie is set before dispatching auth update
          await new Promise(resolve => setTimeout(resolve, 100));

          // Force an immediate auth check to populate the cache
          // This ensures the auth state is ready before navigation
          const { checkAuthStatus } = await import('@/lib/store/authStore').then(m => m.useAuthStore.getState());
          await checkAuthStatus(0, true); // Skip cache, force fresh check

          // Verify the auth state was actually set before proceeding
          const { isAuthenticated, user } = await import('@/lib/store/authStore').then(m => m.useAuthStore.getState());
          if (!isAuthenticated || !user) {
            logger.error('Auth state not set after checkAuthStatus', { component: 'CallbackPage' });
            setStatus('error');
            setErrorMessage('Failed to establish session - please try again');
            return;
          }

          logger.info('Auth state confirmed', { component: 'CallbackPage', userId: user.id });

          // Dispatch custom event to notify other components auth is updated
          window.dispatchEvent(new CustomEvent('auth-update'));
        } catch (authError) {
          logger.error('Authentication failed', authError, { component: 'CallbackPage' });

          // Check if it's a whitelist error
          const errorDetail = (authError as any)?.response?.data?.detail || '';

          if (errorDetail.includes('NOT_WHITELISTED') || errorDetail.includes('not whitelisted')) {
            setStatus('error');
            setErrorType('whitelist');
            setErrorMessage(
              errorDetail.replace('NOT_WHITELISTED: ', '') ||
              'Your Spotify account is not whitelisted for beta access. MoodList is currently in limited beta.'
            );
          } else {
            setStatus('error');
            setErrorType('generic');
            setErrorMessage('Authentication failed - please try again');
          }
          return;
        }

        setStatus('success');

        // Check if there's a stored redirect URL from the auth flow
        const redirectUrl = sessionStorage.getItem('auth_redirect');
        const target = redirectUrl ?? '/';
        setRedirectPath(target);
        if (redirectUrl) {
          sessionStorage.removeItem('auth_redirect'); // Clean up
          // Redirect to the intended destination after a short delay
          setTimeout(() => {
            router.push(redirectUrl);
          }, 2000);
        } else {
          // Default redirect to home page after a short delay
          setTimeout(() => {
            router.push('/');
          }, 2000);
        }

      } catch (error) {
        logger.error('Token exchange failed', error, { component: 'CallbackPage' });
        setStatus('error');
        setErrorMessage('Failed to complete authentication');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  const handleRetry = () => {
    router.push('/');
  };

  return {
    status,
    errorMessage,
    errorType,
    currentStage,
    redirectPath,
    redirectLabel,
    handleRetry,
  };
}
