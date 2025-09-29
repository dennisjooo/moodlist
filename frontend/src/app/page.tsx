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
  const { isAuthenticated, isLoading } = useAuth();

  // Only show loading if we're actually checking auth (not just initializing)
  // If isLoading is true but we have no session cookie, don't show loading
  const hasSessionCookie = typeof document !== 'undefined' && document.cookie.includes('session_token');
  const shouldShowLoading = isLoading && hasSessionCookie;

  if (shouldShowLoading) {
    return (
      <div className="min-h-screen bg-background relative flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-primary rounded-full animate-bounce"></div>
          <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-4 h-4 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    );
  }

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
