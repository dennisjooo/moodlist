import { BoxReveal } from '@/components/ui/box-reveal';
import { MessageCircle, Brain, Music, ArrowDown } from 'lucide-react';

interface TimelineStep {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  color: string;
}

export default function FeaturesSection() {
  const steps: TimelineStep[] = [
    {
      icon: MessageCircle,
      title: 'Describe Your Mood',
      description: 'Tell us how you\'re feeling in your own words - happy, melancholic, energetic, or anything in between',
      color: 'from-blue-500 to-purple-600',
    },
    {
      icon: Brain,
      title: 'AI Analyzes & Understands',
      description: 'Our advanced AI processes your mood and matches it with musical characteristics and genres',
      color: 'from-purple-600 to-pink-600',
    },
    {
      icon: Music,
      title: 'Spotify Creates Your Playlist',
      description: 'A personalized playlist is generated and saved directly to your Spotify account, ready to play',
      color: 'from-pink-600 to-green-500',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mt-16">
      <div className="flex flex-col items-center">
        <BoxReveal boxColor="#8b5cf6" duration={0.5}>
          <h2 className="text-3xl font-bold text-center mb-16">How It Works</h2>
        </BoxReveal>

        <div className="relative w-full">
          {/* Vertical line - mobile: left-aligned, desktop: centered */}
          <div className="absolute left-6 lg:left-1/2 transform -translate-x-1/2 lg:-translate-x-1/2 w-1 bg-gradient-to-b from-blue-500 via-purple-600 via-pink-600 to-green-500 opacity-20 rounded-full h-full"
            ></div>

          <div className="space-y-16 lg:space-y-24">
            {steps.map((step, index) => {
              const IconComponent = step.icon;
              const isLeft = index % 2 === 0;

              return (
                <div key={index} className="relative">
                  {/* Timeline dot - mobile: left-aligned, desktop: centered */}
                  <div className="absolute left-6 lg:left-1/2 transform -translate-x-1/2 lg:-translate-x-1/2 -translate-y-1/2 top-1/2 z-20">
                    <BoxReveal boxColor="#8b5cf6" duration={0.5}>
                      <div className={`w-12 h-12 lg:w-16 lg:h-16 rounded-full bg-gradient-to-br ${step.color} flex items-center justify-center shadow-xl border-4 border-background`}>
                        <IconComponent className="w-6 h-6 lg:w-8 lg:h-8 text-white" />
                      </div>
                    </BoxReveal>
                  </div>

                  {/* Mobile layout: simple left timeline + right content */}
                  <div className="lg:hidden pl-16 ml-4 pr-8">
                    <BoxReveal boxColor="#8b5cf6" duration={0.5}>
                      <div className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10 shadow-lg">
                        <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                        <p className="text-muted-foreground leading-relaxed">
                          {step.description}
                        </p>
                      </div>
                    </BoxReveal>
                  </div>

                  {/* Desktop layout: alternating sides with symmetric spacing */}
                  <div className="hidden lg:grid lg:grid-cols-2 items-center min-h-[120px]">
                    {/* Left side content - always has padding on the right to leave space for center icon */}
                    <div className={`${isLeft ? 'order-1' : 'order-2 lg:order-1'} lg:pr-12`}>
                      {isLeft && (
                        <BoxReveal boxColor="#8b5cf6" duration={0.5}>
                          <div className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10 shadow-lg lg:text-right">
                            <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                            <p className="text-muted-foreground leading-relaxed">
                              {step.description}
                            </p>
                          </div>
                        </BoxReveal>
                      )}
                    </div>

                    {/* Right side content - always has padding on the left to leave space for center icon */}
                    <div className={`${isLeft ? 'order-2' : 'order-1 lg:order-2'} lg:pl-12`}>
                      {!isLeft && (
                        <BoxReveal boxColor="#8b5cf6" duration={0.5}>
                          <div className="bg-white/5 dark:bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10 shadow-lg">
                            <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                            <p className="text-muted-foreground leading-relaxed">
                              {step.description}
                            </p>
                          </div>
                        </BoxReveal>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <BoxReveal boxColor="#8b5cf6" duration={0.5}>
          <div className="mt-16 text-center">
            <p className="text-lg text-muted-foreground">
              Ready to discover your perfect playlist?
            </p>
          </div>
        </BoxReveal>
      </div>
    </div>
  );
}