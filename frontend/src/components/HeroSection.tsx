'use client';

import SpotifyLoginButton from '@/components/SpotifyLoginButton';
import TypewriterText from '@/components/TypewriterText';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Music, ArrowDown } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface HeroSectionProps {
  isLoggedIn: boolean;
}

export default function HeroSection({ isLoggedIn }: HeroSectionProps) {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div className="relative h-screen flex items-center justify-center px-6 lg:px-8">
      <div className="max-w-7xl mx-auto w-full">
        <div className="flex flex-col items-center text-center justify-center h-full">
          <div className="mb-8">
            <Badge variant="outline" className="px-4 py-1 flex items-center gap-2">
              <Music className="w-4 h-4" />
              AI-Powered Playlist Generation
            </Badge>
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl mb-8">
            Turn your mood into<br />{' '}
            <span className="bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
              <TypewriterText
                strings={[
                  'music',
                  'playlists',
                  'vibes',
                  'soundtracks',
                  'beats'
                ]}
                className="inline-block"
              />
            </span>
          </h1>
          <p className="text-lg leading-8 text-muted-foreground max-w-2xl mb-12">
            Describe how you&apos;re feeling and we&apos;ll create the perfect Spotify playlist for your moment.
            Powered by AI, personalized for you.
          </p>

          <div className="flex flex-col items-center mb-16">
            {!isClient ? (
              <div className="flex flex-col items-center space-y-4 min-h-[120px] justify-center">
                {/* Placeholder to prevent layout shift during hydration */}
                <div className="h-12 w-64" />
              </div>
            ) : !isLoggedIn ? (
              <div className="flex flex-col items-center space-y-4 min-h-[120px] justify-center">
                <SpotifyLoginButton />
                <p className="text-sm text-muted-foreground">
                  Connect your Spotify account to get started
                </p>
              </div>
            ) : (
              <div className="w-full max-w-md min-h-[120px] flex items-center justify-center">
                <Button
                  onClick={() => router.push('/create')}
                  className="w-full"
                  size="lg"
                >
                  Create Playlist
                </Button>
              </div>
            )}
          </div>

          {/* Learn More Arrow */}
          <div className="flex flex-col items-center space-y-2 text-muted-foreground">
            <ArrowDown className="w-6 h-6" />
          </div>
        </div>
      </div>
    </div>
  );
}