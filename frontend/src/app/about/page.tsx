import Navigation from '@/components/Navigation';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import { Headphones, Heart, Music, Target, Zap } from 'lucide-react';

export default function AboutPage() {
  const features = [
    {
      icon: Target,
      title: 'AI-Powered Matching',
      description: 'Advanced algorithms analyze your mood and match it with the perfect musical vibe.',
    },
    {
      icon: Zap,
      title: 'Instant Generation',
      description: 'Get your personalized playlist in seconds, not minutes. No waiting, just music.',
    },
    {
      icon: Headphones,
      title: 'Spotify Integration',
      description: 'Seamlessly creates playlists directly in your Spotify account for easy access.',
    },
    {
      icon: Heart,
      title: 'Personal History',
      description: 'Keep track of all your mood-based playlists and revisit your musical journey.',
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
        {/* Hero Section */}
        <div className="text-center mb-16">
          <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
            <Music className="w-4 h-4" />
            About MoodList
          </Badge>

          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-6">
            Music that matches your{' '}
            <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              moment
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            MoodList transforms how you discover music by understanding your emotions and creating
            the perfect soundtrack for every moment of your life.
          </p>
        </div>

        {/* Story Section */}
        <div className="mb-16">
          <Card className="border-0 shadow-lg">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl mb-4">Our Story</CardTitle>
            </CardHeader>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none">
              <p className="text-muted-foreground leading-relaxed">
                We believe that music is more than just sound—it's emotion, memory, and connection.
                MoodList was born from the simple idea that finding the right music for your mood
                shouldn't be a chore. Whether you're feeling nostalgic on a rainy evening, need energy
                for a workout, or want focus music for deep work, we've got you covered.
              </p>
              <p className="text-muted-foreground leading-relaxed mt-4">
                By combining the power of AI with Spotify's vast music library, we create personalized
                playlists that truly understand and enhance your emotional state. Every playlist is
                unique, just like every moment in your life.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Features Grid */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => {
              const IconComponent = feature.icon;
              return (
                <Card key={index} className="border-0 shadow-lg">
                  <CardHeader>
                    <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                      <IconComponent className="w-6 h-6 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Stats Section */}
        <div className="text-center">
          <Card className="border-0 shadow-lg">
            <CardContent className="py-12">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <div className="text-3xl font-bold text-primary mb-2">1,000+</div>
                  <div className="text-muted-foreground">Playlists Created</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-primary mb-2">50+</div>
                  <div className="text-muted-foreground">Mood Categories</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-primary mb-2">∞</div>
                  <div className="text-muted-foreground">Musical Possibilities</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}