import FeaturesSection from '@/components/FeaturesSection';
import HeroSection from '@/components/HeroSection';
import Navigation from '@/components/Navigation';
import PopularMoods from '@/components/PopularMoods';
import dynamic from 'next/dynamic';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cookies } from 'next/headers';
import { cn } from '@/lib/utils';

const SocialProof = dynamic(() => import('@/components/SocialProof'), {
  loading: () => <div className="h-[120px]" />,
});

export default async function Home() {
  const cookieStore = await cookies();
  const isLoggedIn = Boolean(cookieStore.get('session_token'));

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

      {/* Navigation - Always render */}
      <Navigation />

      {/* Main Content - Render immediately (optimistic) */}
      <main className="relative z-10">
        {/* Hero Section */}
        <HeroSection
          isLoggedIn={isLoggedIn}
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
