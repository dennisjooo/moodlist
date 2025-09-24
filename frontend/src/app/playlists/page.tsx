'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import Navigation from '@/components/Navigation';
import PlaylistCard from '@/components/PlaylistCard';
import { Music } from 'lucide-react';

export default function PlaylistsPage() {
  // Mock data - will be replaced with real data from backend
  const playlists = [
    {
      id: 1,
      mood: 'Chill evening vibes',
      title: 'Chill Evening Vibes',
      createdAt: '2024-01-15',
      trackCount: 25,
      spotifyUrl: '#',
    },
    {
      id: 2,
      mood: 'Energetic workout',
      title: 'Energetic Workout',
      createdAt: '2024-01-14',
      trackCount: 30,
      spotifyUrl: '#',
    },
    {
      id: 3,
      mood: 'Focus and productivity',
      title: 'Focus and Productivity',
      createdAt: '2024-01-12',
      trackCount: 20,
      spotifyUrl: '#',
    },
    {
      id: 4,
      mood: 'Road trip adventure',
      title: 'Road Trip Adventure',
      createdAt: '2024-01-10',
      trackCount: 35,
      spotifyUrl: '#',
    },
    {
      id: 5,
      mood: 'Romantic night',
      title: 'Romantic Night',
      createdAt: '2024-01-08',
      trackCount: 18,
      spotifyUrl: '#',
    },
    {
      id: 6,
      mood: 'Morning coffee',
      title: 'Morning Coffee',
      createdAt: '2024-01-05',
      trackCount: 22,
      spotifyUrl: '#',
    },
  ];

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

        {playlists.length === 0 ? (
          <div className="text-center py-12">
            <Music className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">No playlists yet</h3>
            <p className="text-muted-foreground mb-6">
              Create your first mood-based playlist to get started!
            </p>
            <Button>Create Playlist</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {playlists.map((playlist) => (
              <PlaylistCard
                key={playlist.id}
                id={playlist.id}
                mood={playlist.mood}
                title={playlist.title}
                createdAt={playlist.createdAt}
                trackCount={playlist.trackCount}
                spotifyUrl={playlist.spotifyUrl}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}