'use client';

import { AuthGuard } from '@/components/AuthGuard';
import Navigation from '@/components/Navigation';
import PlaylistCard from '@/components/PlaylistCard';
import { SpotifyLoginButton } from '@/components/features/auth/SpotifyLoginButton';
import { PlaylistGridSkeleton } from '@/components/shared/LoadingStates';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import { playlistAPI, UserPlaylist } from '@/lib/playlistApi';
import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { motion } from '@/components/ui/lazy-motion';
import { Music } from 'lucide-react';
import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';

function PlaylistsPageContent() {
  const [playlists, setPlaylists] = useState<UserPlaylist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUnauthorized, setIsUnauthorized] = useState(false);

  const fetchPlaylists = async () => {
    try {
      setIsLoading(true);
      setIsUnauthorized(false);
      const response = await playlistAPI.getUserPlaylists();
      setPlaylists(response.playlists);
    } catch (err) {
      logger.error('Failed to fetch playlists', err, { component: 'PlaylistsPage' });
      const errorMessage = err instanceof Error ? err.message : 'Failed to load playlists';

      // Check if it's a 401 Unauthorized error
      if (errorMessage.includes('401')) {
        setIsUnauthorized(true);
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlaylists();
  }, []);

  const handleDelete = async (playlistId: number) => {
    try {
      await playlistAPI.deletePlaylist(playlistId);
      // Remove from local state
      setPlaylists(prev => prev.filter(p => p.id !== playlistId));
    } catch (err) {
      logger.error('Failed to delete playlist', err, { component: 'PlaylistsPage' });
      setError('Failed to delete playlist. Please try again.');
      // Clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    }
  };


  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-background relative">
      {/* Fixed Dot Pattern Background */}
      <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
          )}
        />
      </div>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <CrossfadeTransition
          isLoading={isLoading}
          skeleton={<PlaylistGridSkeleton />}
        >
          <div className="space-y-12">
            {!isUnauthorized && (
              <div className="text-center">
                <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                  <Music className="w-4 h-4" />
                  Your Music History
                </Badge>

                <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                  My Playlists
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  All your mood-based playlists in one place. Relive your musical moments.
                </p>
              </div>
            )}

            {isUnauthorized ? (
              <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4 }}
                  className="text-center max-w-lg mx-auto"
                >
                  <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-2xl font-semibold mb-3">Login to View Your Playlists</h3>
                  <p className="text-muted-foreground mb-8">
                    Connect your Spotify account to access your personalized mood-based playlists.
                    All your musical moments, saved in one place.
                  </p>
                  <div className="flex justify-center mb-6">
                    <SpotifyLoginButton />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    New here? Create your first playlist after logging in!
                  </p>
                </motion.div>
              </div>
            ) : error ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="text-center py-12"
              >
                <Music className="w-16 h-16 text-destructive mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Failed to load playlists</h3>
                <p className="text-muted-foreground mb-6">{error}</p>
                <Button onClick={() => fetchPlaylists()}>Try Again</Button>
              </motion.div>
            ) : playlists.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="text-center py-12"
              >
                <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No playlists yet</h3>
                <p className="text-muted-foreground mb-6">
                  Create your first mood-based playlist to get started!
                </p>
                <Link href="/create">
                  <Button>Create Playlist</Button>
                </Link>
              </motion.div>
            ) : (
              <motion.div
                initial="hidden"
                animate="visible"
                variants={{
                  visible: {
                    transition: {
                      staggerChildren: 0.1
                    }
                  }
                }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              >
                {playlists.map((playlist) => (
                  <motion.div
                    key={playlist.id}
                    variants={{
                      hidden: { opacity: 0, y: 20 },
                      visible: { opacity: 1, y: 0 }
                    }}
                    transition={{ duration: 0.4 }}
                  >
                    <PlaylistCard
                      mood={playlist.mood_prompt}
                      title={playlist.name || playlist.mood_prompt}
                      createdAt={formatDate(playlist.created_at)}
                      trackCount={playlist.track_count}
                      spotifyUrl={playlist.spotify_url || '#'}
                      sessionId={playlist.session_id}
                      status={playlist.status}
                      playlistId={playlist.id}
                      moodAnalysis={playlist.mood_analysis_data}
                      onDelete={handleDelete}
                      colorPrimary={playlist.color_primary}
                      colorSecondary={playlist.color_secondary}
                      colorTertiary={playlist.color_tertiary}
                    />
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>
        </CrossfadeTransition>
      </main>
    </div>
  );
}

export default function PlaylistsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background relative">
        {/* Fixed Dot Pattern Background */}
        <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
          <DotPattern
            className={cn(
              "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
            )}
          />
        </div>
        <Navigation />
        <main className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <PlaylistGridSkeleton />
        </main>
      </div>
    }>
      <AuthGuard optimistic={true}>
        <PlaylistsPageContent />
      </AuthGuard>
    </Suspense>
  );
}