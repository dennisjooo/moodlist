import SpotifyLoginButton from '@/components/SpotifyLoginButton';
import TypewriterText from '@/components/TypewriterText';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Music } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface HeroSectionProps {
  isLoggedIn: boolean;
  onLoginSuccess?: () => void;
}

export default function HeroSection({ isLoggedIn, onLoginSuccess }: HeroSectionProps) {
  const router = useRouter();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="py-16 lg:py-24">
        <div className="flex flex-col items-center text-center">
          <div className="mb-6">
            <Badge variant="outline" className="px-4 py-1 flex items-center gap-2">
              <Music className="w-4 h-4" />
              AI-Powered Playlist Generation
            </Badge>
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl">
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
          <p className="mt-6 text-lg leading-8 text-muted-foreground max-w-2xl">
            Describe how you're feeling and we'll create the perfect Spotify playlist for your moment.
            Powered by AI, personalized for you.
          </p>

          <div className="mt-10 flex flex-col items-center">
            {!isLoggedIn ? (
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
        </div>
      </div>
    </div>
  );
}