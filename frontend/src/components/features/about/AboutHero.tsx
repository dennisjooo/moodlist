'use client';

import Navigation from '@/components/Navigation';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { DotPattern } from '@/components/ui/dot-pattern';
import { motion } from '@/components/ui/lazy-motion';
import { cn } from '@/lib/utils';
import { Music } from 'lucide-react';

export function AboutHero() {
    return (
        <>
            {/* Fixed Dot Pattern Background */}
            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeIn_1s_ease-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            {/* Navigation */}
            <Navigation />

            {/* Hero Section */}
            <motion.div
                className="relative z-10 max-w-3xl mx-auto px-8 pt-16 sm:pt-24"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
            >
                <div className="space-y-4">
                    <FeatureBadge icon={Music} className="mb-6">
                        The Story Behind MoodList
                    </FeatureBadge>

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
            </motion.div>
        </>
    );
}
