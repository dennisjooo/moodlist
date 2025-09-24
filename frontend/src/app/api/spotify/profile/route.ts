import { NextRequest, NextResponse } from 'next/server';

interface SpotifyProfileResponse {
  id: string;
  display_name: string;
  email: string;
  images: Array<{ url: string; height: number; width: number }>;
  country: string;
  followers: { total: number };
  product?: string;
}

interface ProfileError {
  error: string;
  error_description?: string;
}

/**
 * Validates the Authorization header and extracts the access token
 */
function extractAccessToken(request: NextRequest): string | null {
  const authHeader = request.headers.get('authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  return authHeader.replace('Bearer ', '');
}

/**
 * Fetches user profile from Spotify API
 */
async function fetchSpotifyProfile(accessToken: string): Promise<SpotifyProfileResponse> {
  const profileResponse = await fetch('https://api.spotify.com/v1/me', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });

  if (!profileResponse.ok) {
    const errorData: ProfileError = await profileResponse.json().catch(() => ({}));
    console.error('Spotify profile fetch failed:', profileResponse.status, profileResponse.statusText, errorData);
    throw new Error(`Profile fetch failed: ${profileResponse.status} ${profileResponse.statusText}`);
  }

  const profileData: SpotifyProfileResponse = await profileResponse.json();

  // Validate required fields
  if (!profileData.id || !profileData.display_name) {
    throw new Error('Invalid profile response: missing required fields');
  }

  return profileData;
}

/**
 * Sanitizes and formats profile data for client response
 */
function formatProfileResponse(profileData: SpotifyProfileResponse) {
  return {
    id: profileData.id,
    display_name: profileData.display_name,
    email: profileData.email,
    images: profileData.images || [],
    country: profileData.country || '',
    followers: profileData.followers?.total || 0,
  };
}

export async function GET(request: NextRequest) {
  try {
    // Extract and validate access token
    const accessToken = extractAccessToken(request);

    if (!accessToken) {
      console.error('Profile API - No valid access token provided');
      return NextResponse.json(
        { error: 'Access token required' },
        { status: 401 }
      );
    }

    // Fetch user profile from Spotify
    const profileData = await fetchSpotifyProfile(accessToken);

    // Format and return profile data
    const responseData = formatProfileResponse(profileData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('Profile fetch error:', error);

    // Determine appropriate error response based on error type
    if (error instanceof Error) {
      if (error.message.includes('Profile fetch failed')) {
        return NextResponse.json(
          { error: 'Failed to fetch user profile' },
          { status: 500 }
        );
      }

      if (error.message.includes('Invalid profile response')) {
        return NextResponse.json(
          { error: 'Invalid profile data received' },
          { status: 502 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}