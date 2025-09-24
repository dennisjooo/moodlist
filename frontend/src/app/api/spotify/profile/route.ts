import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const accessToken = request.headers.get('authorization')?.replace('Bearer ', '');

    if (!accessToken) {
      console.error('Profile API - No access token provided');
      return NextResponse.json(
        { error: 'Access token required' },
        { status: 401 }
      );
    }

    // Fetch user profile from Spotify
    const profileResponse = await fetch('https://api.spotify.com/v1/me', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!profileResponse.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch user profile' },
        { status: 500 }
      );
    }

    const profileData = await profileResponse.json();

    const responseData = {
      id: profileData.id,
      display_name: profileData.display_name,
      email: profileData.email,
      images: profileData.images,
      country: profileData.country,
      followers: profileData.followers?.total || 0,
    };

    return NextResponse.json(responseData);

  } catch (error) {
    console.error('Profile fetch error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}