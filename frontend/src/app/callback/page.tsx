'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Music, CheckCircle, XCircle } from 'lucide-react';

export default function CallbackPage() {
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
      const storedState = localStorage.getItem('spotify_auth_state');
      if (state !== storedState) {
        setStatus('error');
        setErrorMessage('Security validation failed');
        localStorage.removeItem('spotify_auth_state');
        return;
      }
      localStorage.removeItem('spotify_auth_state');

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
        // Exchange code for tokens
        const tokenResponse = await fetch('/api/spotify/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code }),
        });

        if (!tokenResponse.ok) {
          throw new Error('Failed to exchange code for tokens');
        }

        const tokenData = await tokenResponse.json();

        // Store tokens in localStorage or state management
        localStorage.setItem('spotify_access_token', tokenData.access_token);
        localStorage.setItem('spotify_refresh_token', tokenData.refresh_token);

        // Fetch and store user profile
        try {
          const profileResponse = await fetch('/api/spotify/profile', {
            headers: {
              'Authorization': `Bearer ${tokenData.access_token}`,
            },
          });

          if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            console.log('Profile data fetched:', profileData);
            localStorage.setItem('spotify_user_profile', JSON.stringify(profileData));
            console.log('Profile stored in localStorage');

            // Dispatch custom event to notify other components
            window.dispatchEvent(new CustomEvent('spotify-profile-update'));
          } else {
            console.error('Profile fetch failed:', profileResponse.status, profileResponse.statusText);
          }
        } catch (profileError) {
          console.error('Failed to fetch user profile:', profileError);
          // Continue with login even if profile fetch fails
        }

        setStatus('success');

        // Redirect to create page after a short delay
        setTimeout(() => {
          router.push('/create');
        }, 2000);

      } catch (error) {
        console.error('Token exchange failed:', error);
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