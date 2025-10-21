'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/authContext';
import { config } from '@/lib/config';
import { getAuthCookies } from '@/lib/cookies';
import { logger } from '@/lib/utils/logger';
import { ArrowLeft, Mail, MapPin, Music, User, Users } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface SpotifyProfile {
  id: string;
  display_name: string;
  email?: string;
  images: Array<{ url: string; height: number; width: number }>;
  country?: string;
  followers: number;
}

function ProfilePageContent() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const [spotifyProfile, setSpotifyProfile] = useState<SpotifyProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchSpotifyProfile();
    }
  }, [isAuthenticated, user]);

  const fetchSpotifyProfile = async () => {
    if (!user) return;

    try {
      setProfileLoading(true);
      const backendUrl = config.api.baseUrl;

      const response = await fetch(`${backendUrl}/api/spotify/profile`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthCookies(),
        },
        credentials: 'include',
      });

      if (response.ok) {
        const profileData = await response.json();
        setSpotifyProfile(profileData);
      } else if (response.status === 401) {
        // Not authenticated, redirect to home
        router.push('/');
      } else {
        logger.error('Failed to fetch Spotify profile', undefined, { component: 'ProfilePage' });
      }
    } catch (error) {
      logger.error('Error fetching Spotify profile', error, { component: 'ProfilePage' });
    } finally {
      setProfileLoading(false);
    }
  };

  const handleBack = () => {
    router.back();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={handleBack}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>

          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center">
              <Music className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Profile</h1>
              <p className="text-muted-foreground">Your connected Spotify account</p>
            </div>
          </div>
        </div>

        {/* Profile Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <User className="w-5 h-5" />
              <span>Profile Information</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-6">
              {/* Profile Picture */}
              <div className="flex-shrink-0">
                {spotifyProfile?.images?.[0]?.url ? (
                  <Image
                    src={spotifyProfile.images[0].url}
                    alt={spotifyProfile.display_name}
                    width={120}
                    height={120}
                    className="rounded-full"
                  />
                ) : (
                  <div className="w-30 h-30 bg-primary/10 rounded-full flex items-center justify-center">
                    <User className="w-12 h-12 text-primary" />
                  </div>
                )}
              </div>

              {/* Profile Details */}
              <div className="flex-1 space-y-4">
                <div>
                  <h2 className="text-2xl font-semibold">{user?.display_name}</h2>
                  <p className="text-muted-foreground">@{user?.spotify_id}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {user?.email && (
                    <div className="flex items-center space-x-2">
                      <Mail className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{user?.email}</span>
                    </div>
                  )}

                  {spotifyProfile?.country && (
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{spotifyProfile.country}</span>
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">{spotifyProfile?.followers.toLocaleString() || 0} followers</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* App Usage Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Music className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-1">Playlists Generated</h3>
                <p className="text-2xl font-bold text-primary">--</p>
                <p className="text-xs text-muted-foreground">Coming soon</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <User className="w-6 h-6 text-green-600" />
                </div>
                <h3 className="font-semibold mb-1">Moods Analyzed</h3>
                <p className="text-2xl font-bold text-green-600">--</p>
                <p className="text-xs text-muted-foreground">Coming soon</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="font-semibold mb-1">App Sessions</h3>
                <p className="text-2xl font-bold text-blue-600">--</p>
                <p className="text-xs text-muted-foreground">Coming soon</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <AuthGuard optimistic={false}>
      <ProfilePageContent />
    </AuthGuard>
  );
}