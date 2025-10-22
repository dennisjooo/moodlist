'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle, Music, XCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
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
        const tokenResponse = await fetch(`${backendUrl}/api/spotify/token?code=${encodeURIComponent(code)}`, {
          method: 'POST',
        });

        if (!tokenResponse.ok) {
          throw new Error('Failed to exchange code for tokens');
        }

        const tokenData = await tokenResponse.json();

        // Use new authentication system
        try {
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

        // Redirect to home page after a short delay
        setTimeout(() => {
          router.push('/');
        }, 2000);

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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            {status === 'loading' && (
              <div className="p-3 rounded-full bg-primary/10">
                <Music className="w-8 h-8 text-primary" />
              </div>
            )}

            {status === 'loading' && (
              <>
                <h1 className="text-2xl font-semibold">Connecting to Spotify</h1>
                <p className="text-muted-foreground">
                  Please wait while we complete your authentication...
                </p>
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </>
            )}

            {status === 'success' && (
              <>
                <CheckCircle className="w-12 h-12 text-green-500" />
                <h1 className="text-2xl font-semibold text-green-600">Connected Successfully!</h1>
                <p className="text-muted-foreground">
                  Your Spotify account has been connected. Redirecting to create your playlist...
                </p>
              </>
            )}

            {status === 'error' && (
              <>
                <XCircle className="w-12 h-12 text-red-500" />
                <h1 className="text-2xl font-semibold text-red-600">Connection Failed</h1>
                <p className="text-muted-foreground">
                  {errorMessage}
                </p>
                <Button onClick={handleRetry} className="w-full">
                  Try Again
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center space-y-4">
              <div className="p-3 rounded-full bg-primary/10">
                <Music className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-2xl font-semibold">Loading...</h1>
              <p className="text-muted-foreground">
                Preparing authentication...
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
