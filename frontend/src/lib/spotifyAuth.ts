/**
 * Shared Spotify OAuth utility functions
 */

import { logger } from '@/lib/utils/logger';

export interface SpotifyAuthConfig {
  clientId: string;
  redirectUri: string;
  scope: string;
}

/**
 * Initiates Spotify OAuth flow
 */
export function initiateSpotifyAuth(): void {
  const clientId = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID;
  const redirectUri = process.env.NEXT_PUBLIC_SPOTIFY_REDIRECT_URI || 'http://localhost:3000/callback';
  const scope = 'playlist-modify-public playlist-modify-private user-read-private user-read-email user-top-read ugc-image-upload';

  if (!clientId) {
    logger.error('Spotify Client ID not configured', undefined, { component: 'spotifyAuth' });
    return;
  }

  // Generate random state for security
  const state = Math.random().toString(36).substring(2, 15);
  sessionStorage.setItem('spotify_auth_state', state);

  // Construct Spotify authorization URL
  const authUrl = new URL('https://accounts.spotify.com/authorize');
  authUrl.searchParams.append('client_id', clientId);
  authUrl.searchParams.append('response_type', 'code');
  authUrl.searchParams.append('redirect_uri', redirectUri);
  authUrl.searchParams.append('scope', scope);
  authUrl.searchParams.append('state', state);

  // Redirect to Spotify
  window.location.href = authUrl.toString();
}

/**
 * Validates if Spotify OAuth is properly configured
 */
export function isSpotifyAuthConfigured(): boolean {
  const clientId = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID;
  return Boolean(clientId);
}