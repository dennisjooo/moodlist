import HeroSection from '@/components/HeroSection';
import Navigation from '@/components/Navigation';
import dynamic from 'next/dynamic';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cookies } from 'next/headers';
import { cn } from '@/lib/utils';

// Lazy load below-the-fold components for better initial load performance
const FeaturedMoodShowcase = dynamic(() => import('@/components/FeaturedMoodShowcase'), {
    loading: () => <div className="h-[420px]" />,
});

const SampleMoods = dynamic(() => import('@/components/SampleMoods'), {
  loading: () => <div className="h-[320px]" />,
});

const FeaturesSection = dynamic(() => import('@/components/FeaturesSection'), {
  loading: () => <div className="h-[400px]" />,
});

const FAQSection = dynamic(
  () => import('@/components/features/marketing/FAQSection'),
  {
    loading: () => <div className="h-[420px]" />,
  }
);

const CTASection = dynamic(
  () => import('@/components/features/marketing/CTASection'),
  {
    loading: () => <div className="h-[280px]" />,
  }
);

const SocialProof = dynamic(() => import('@/components/SocialProof'), {
  loading: () => <div className="h-[120px]" />,
});

export default async function Home() {
  const cookieStore = await cookies();
  const isLoggedIn = Boolean(cookieStore.get('session_token'));

  return (
    <div className="min-h-screen bg-background relative overflow-x-hidden">
      {/* Fixed Dot Pattern Background */}
      <div className="fixed inset-0 z-0 opacity-0 animate-[fadeIn_1s_ease-in-out_forwards] overflow-hidden">
        <DotPattern
          className={cn(
            "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
          )}
        />
      </div>

      {/* Navigation - Always render */}
      <Navigation />

      {/* Main Content - Render immediately (optimistic) */}
      <main className="relative z-10 overflow-x-hidden">
        {/* Hero Section */}
        <HeroSection
          isLoggedIn={isLoggedIn}
        />

        {/* Featured Mood Walkthrough */}
        <FeaturedMoodShowcase />

        {/* Sample Moods */}
        <SampleMoods />

        {/* Features */}
        <FeaturesSection />

        {/* Frequently Asked Questions */}
        <FAQSection />

        {/* Call to Action */}
        <CTASection isLoggedIn={isLoggedIn} />

        {/* Social Proof */}
        <SocialProof />
      </main>
    </div>
  );
}
