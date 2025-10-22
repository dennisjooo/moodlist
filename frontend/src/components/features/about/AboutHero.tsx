import Navigation from '@/components/Navigation';
import { Badge } from '@/components/ui/badge';
import { DotPattern } from '@/components/ui/dot-pattern';
import { cn } from '@/lib/utils';
import { Music } from 'lucide-react';

export function AboutHero() {
    return (
        <>
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

            {/* Hero Section */}
            <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24">
                <Badge variant="outline" className="px-3 py-1 flex items-center gap-2 w-fit mx-auto mb-6 text-xs font-medium border-primary/20">
                    <Music className="w-3.5 h-3.5" />
                    The Story Behind MoodList
                </Badge>

                <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground mb-4 leading-tight">
                    Building a playlist generator{' '}
                    <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        from scratch
                    </span>
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl leading-relaxed">
                    A journey through AI agents, API integrations, and the messy reality of full-stack development.
                </p>
            </div>
        </>
    );
}
