'use client';

import { useState, useEffect } from 'react';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import Navigation from '@/components/Navigation';
import HeroSection from '@/components/HeroSection';
import PopularMoods from '@/components/PopularMoods';
import FeaturesSection from '@/components/FeaturesSection';
import SocialProof from '@/components/SocialProof';
import { ToastContainer, useToast } from '@/components/ui/toast';

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const { toasts, removeToast } = useToast();

  // Check for existing Spotify tokens on page load
  useEffect(() => {
    const accessToken = localStorage.getItem('spotify_access_token');
    const refreshToken = localStorage.getItem('spotify_refresh_token');
    if (accessToken && refreshToken) setIsLoggedIn(true);
  }, []);

  const handleLoginSuccess = () => setIsLoggedIn(true);

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

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      {/* Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="relative z-10">
        {/* Hero Section */}
        <HeroSection
          isLoggedIn={isLoggedIn}
          onLoginSuccess={handleLoginSuccess}
        />

        {/* Popular Moods */}
        <PopularMoods />

        {/* Features */}
        <FeaturesSection />

        {/* Social Proof */}
        <SocialProof />
      </main>
    </div>
  );
}
