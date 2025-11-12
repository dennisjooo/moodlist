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
 * Generate a random string for PKCE code verifier
 */
function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate PKCE code challenge from verifier
 */
async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)));
  return base64
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Initiates Spotify OAuth flow with PKCE
 */
export async function initiateSpotifyAuth(): Promise<void> {
  const clientId = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID;
  const redirectUri = process.env.NEXT_PUBLIC_SPOTIFY_REDIRECT_URI || 'http://127.0.0.1:3000/callback';
  const scope = 'playlist-read-private playlist-modify-public playlist-modify-private user-read-private user-read-email user-top-read ugc-image-upload';

  if (!clientId) {
    logger.error('Spotify Client ID not configured', undefined, { component: 'spotifyAuth' });
    return;
  }

  // Generate random state for security
  const state = Math.random().toString(36).substring(2, 15);
  sessionStorage.setItem('spotify_auth_state', state);

  // Generate PKCE code verifier and challenge
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Store code verifier for token exchange
  sessionStorage.setItem('spotify_code_verifier', codeVerifier);

  // Construct Spotify authorization URL with PKCE
  const authUrl = new URL('https://accounts.spotify.com/authorize');
  authUrl.searchParams.append('client_id', clientId);
  authUrl.searchParams.append('response_type', 'code');
  authUrl.searchParams.append('redirect_uri', redirectUri);
  authUrl.searchParams.append('scope', scope);
  authUrl.searchParams.append('state', state);
  authUrl.searchParams.append('code_challenge_method', 'S256');
  authUrl.searchParams.append('code_challenge', codeChallenge);

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