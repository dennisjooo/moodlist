import { NextRequest, NextResponse } from 'next/server';

interface TokenExchangeRequest {
  code: string;
}

interface SpotifyTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  scope: string;
}

interface TokenExchangeError {
  error: string;
  error_description?: string;
}

/**
 * Exchanges Spotify authorization code for access tokens
 */
async function exchangeCodeForTokens(
  code: string,
  clientId: string,
  clientSecret: string,
  redirectUri: string
): Promise<SpotifyTokenResponse> {
  const tokenResponse = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`,
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
    }),
  });

  if (!tokenResponse.ok) {
    const errorData: TokenExchangeError = await tokenResponse.json().catch(() => ({}));
    console.error('Token exchange failed:', tokenResponse.status, tokenResponse.statusText, errorData);
    throw new Error(`Token exchange failed: ${tokenResponse.status} ${tokenResponse.statusText}`);
  }

  const tokenData: SpotifyTokenResponse = await tokenResponse.json();

  // Validate required fields
  if (!tokenData.access_token || !tokenData.refresh_token) {
    throw new Error('Invalid token response: missing required fields');
  }

  return tokenData;
}

/**
 * Validates required environment variables for Spotify OAuth
 */
function validateSpotifyConfig(): { clientId: string; clientSecret: string; redirectUri: string } {
  const clientId = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID;
  const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;
  const redirectUri = process.env.NEXT_PUBLIC_SPOTIFY_REDIRECT_URI || 'http://127.0.0.1:3000/callback';

  if (!clientId || !clientSecret) {
    throw new Error('Missing Spotify OAuth credentials: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be configured');
  }

  return { clientId, clientSecret, redirectUri };
}

export async function POST(request: NextRequest) {
  try {
    // Parse and validate request body
    const body: TokenExchangeRequest = await request.json();
    const { code } = body;

    if (!code || typeof code !== 'string') {
      return NextResponse.json(
        { error: 'Authorization code is required and must be a string' },
        { status: 400 }
      );
    }

    // Validate environment configuration
    const { clientId, clientSecret, redirectUri } = validateSpotifyConfig();

    // Exchange authorization code for tokens
    const tokenData = await exchangeCodeForTokens(code, clientId, clientSecret, redirectUri);

    // Return sanitized token data
    return NextResponse.json({
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      expires_in: tokenData.expires_in,
    });

  } catch (error) {
    console.error('Token exchange error:', error);

    // Determine appropriate error response based on error type
    if (error instanceof Error) {
      if (error.message.includes('Missing Spotify OAuth credentials')) {
        return NextResponse.json(
          { error: 'Server configuration error' },
          { status: 500 }
        );
      }

      if (error.message.includes('Token exchange failed')) {
        return NextResponse.json(
          { error: 'Failed to exchange authorization code' },
          { status: 500 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}