'use client';

import Navigation from '@/components/Navigation';
import PlaylistCard from '@/components/PlaylistCard';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import { playlistAPI, UserPlaylist } from '@/lib/playlistApi';
import { Music } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function PlaylistsPage() {
  const [playlists, setPlaylists] = useState<UserPlaylist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlaylists = async () => {
    try {
      setIsLoading(true);
      const response = await playlistAPI.getUserPlaylists();
      setPlaylists(response.playlists);
    } catch (err) {
      console.error('Failed to fetch playlists:', err);
      setError(err instanceof Error ? err.message : 'Failed to load playlists');
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
      console.error('Failed to delete playlist:', err);
      setError('Failed to delete playlist. Please try again.');
      // Clear error after 5 seconds
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleCardClick = (playlist: UserPlaylist) => {
    // If completed and has Spotify URL, go directly to Spotify
    if (playlist.status === 'completed' && playlist.spotify_url) {
      window.open(playlist.spotify_url, '_blank');
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
        <div className="text-center mb-12">
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

        {isLoading ? (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-primary rounded-full animate-bounce"></div>
              <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <Music className="w-16 h-16 text-destructive mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Failed to load playlists</h3>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button onClick={() => window.location.reload()}>Try Again</Button>
          </div>
        ) : playlists.length === 0 ? (
          <div className="text-center py-12">
            <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No playlists yet</h3>
            <p className="text-muted-foreground mb-6">
              Create your first mood-based playlist to get started!
            </p>
            <Link href="/create">
              <Button>Create Playlist</Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {playlists.map((playlist) => (
              <div key={playlist.id} onClick={() => handleCardClick(playlist)}>
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
                />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}