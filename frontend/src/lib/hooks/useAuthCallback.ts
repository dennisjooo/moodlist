import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

export type AuthStatus = 'loading' | 'success' | 'error';

export interface AuthCallbackState {
  status: AuthStatus;
  errorMessage: string;
  currentStage: number;
  redirectPath: string | null;
  redirectLabel: string;
}

function deriveRedirectLabel(path: string | null) {
  if (!path || path === "/") {
    return "your dashboard";
  }

  try {
    const base =
      typeof window !== "undefined" ? window.location.origin : "https://moodlist.app";
    const url = new URL(path, base);
    if (!url.pathname || url.pathname === "/") {
      return "your dashboard";
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
        const backendUrl = config.api.baseUrl;
        setCurrentStage(1);
        const tokenResponse = await fetch(`${backendUrl}/api/spotify/token?code=${encodeURIComponent(code)}`, {
          method: 'POST',
        });

        if (!tokenResponse.ok) {
          throw new Error('Failed to exchange code for tokens');
        }

        const tokenData = await tokenResponse.json();

        // Use new authentication system
        try {
          // Begin finalizing session
          // Register/Login through backend API (this will set session cookies)
          const response = await fetch(`${backendUrl}/api/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              access_token: tokenData.access_token,
              refresh_token: tokenData.refresh_token,
              token_expires_at: Date.now() + (tokenData.expires_in * 1000),
            }),
          });

          if (!response.ok) {
            throw new Error(`Authentication failed: ${response.status}`);
          }

          setCurrentStage(2);

          // Add a small delay to ensure cookie is set before dispatching auth update
          await new Promise(resolve => setTimeout(resolve, 100));

          // Dispatch custom event to notify other components to refresh auth state
          window.dispatchEvent(new CustomEvent('auth-update'));
        } catch (authError) {
          logger.error('Authentication failed', authError, { component: 'CallbackPage' });
          setStatus('error');
          setErrorMessage('Authentication failed - please try again');
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
    currentStage,
    redirectPath,
    redirectLabel,
    handleRetry,
  };
}
