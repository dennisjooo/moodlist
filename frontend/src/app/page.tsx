'use client';

import FeaturesSection from '@/components/FeaturesSection';
import HeroSection from '@/components/HeroSection';
import Navigation from '@/components/Navigation';
import PopularMoods from '@/components/PopularMoods';
import SocialProof from '@/components/SocialProof';
import { DotPattern } from '@/components/ui/dot-pattern';
import { ToastContainer, useToast } from '@/components/ui/toast';
import { useAuth } from '@/lib/authContext';
import { cn } from '@/lib/utils';

export default function Home() {
  const { toasts, removeToast } = useToast();
  const { isAuthenticated } = useAuth();

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

      {/* Navigation - Always render */}
      <Navigation />

      {/* Main Content - Render immediately (optimistic) */}
      <main className="relative z-10">
        {/* Hero Section */}
        <HeroSection
          isLoggedIn={isAuthenticated}
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
