'use client';

import { useState, useEffect } from 'react';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import MoodInput from '@/components/MoodInput';
import MoodCard from '@/components/MoodCard';
import Navigation from '@/components/Navigation';
import { Badge } from '@/components/ui/badge';
import { Music } from 'lucide-react';

export default function CreatePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleMoodSubmit = (mood: string) => {
    console.log('Mood submitted:', mood);
    // This will be connected to the backend later
  };

  const mobileMoods = [
    'Chill Evening',
    'Energetic Workout',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
  ];

  const desktopMoods = [
    'Chill Evening',
    'Energetic Workout',
    'Study Focus',
    'Road Trip',
    'Romantic Night',
    'Morning Coffee',
    'Rainy Day',
    'Party Vibes',
    'Happy Sunshine',
    'Melancholy Blues',
    'Adventure Time',
    'Cozy Winter',
  ];

  const moods = isMobile ? mobileMoods : desktopMoods;

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
      <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
            <Music className="w-4 h-4" />
            Create Your Playlist
          </Badge>

          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
            What's your mood?
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Describe how you're feeling and we'll create the perfect Spotify playlist for your moment.
          </p>
        </div>

        <div className="flex justify-center">
          <div className="w-full max-w-md">
            <MoodInput onSubmit={handleMoodSubmit} />
          </div>
        </div>

        {/* Quick Mood Suggestions */}
        <div className="mt-16">
          <h2 className="text-2xl font-semibold text-center mb-8">Quick Suggestions</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
            {moods.map((mood, index) => (
              <MoodCard
                key={index}
                mood={mood}
                onClick={() => handleMoodSubmit(mood)}
              />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}