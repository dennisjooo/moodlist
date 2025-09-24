'use client';

import { useState } from 'react';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import Navigation from '@/components/Navigation';
import HeroSection from '@/components/HeroSection';
import PopularMoods from '@/components/PopularMoods';
import FeaturesSection from '@/components/FeaturesSection';
import SocialProof from '@/components/SocialProof';

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleMoodSubmit = (mood: string) => {
    console.log('Mood submitted:', mood);
    // This will be connected to the backend later
  };

  const handleSpotifyLogin = () => {
    console.log('Spotify login initiated');
    // This will trigger the OAuth flow later
    setIsLoggedIn(true);
  };

  return (
    <div className="min-h-screen bg-background relative">
      {/* Fixed Dot Pattern Background */}
      <div className="fixed inset-0 z-0 opacity-0 animate-[fadeIn_1s_ease-in-out_forwards]">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
          )}
        />
      </div>

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10">
        {/* Hero Section */}
        <HeroSection
          isLoggedIn={isLoggedIn}
          onSpotifyLogin={handleSpotifyLogin}
          onMoodSubmit={handleMoodSubmit}
        />

        {/* Popular Moods */}
        <PopularMoods isLoggedIn={isLoggedIn} />

        {/* Features */}
        <FeaturesSection />

        {/* Social Proof */}
        <SocialProof />
      </main>
    </div>
  );
}
