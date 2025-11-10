'use client';

import SampleMoods from '@/components/features/marketing/SampleMoods/SampleMoods';
import { Button } from '@/components/ui/button';
import { FeatureBadge } from '@/components/ui/feature-badge';
import { motion } from '@/components/ui/lazy-motion';
import { BUTTON_MOTION_PROPS, SPRING_TRANSITIONS, STAGGER_CONTAINER_VARIANTS, STAGGER_ITEM_VARIANTS } from '@/lib/constants/animations';
import { Sparkles } from 'lucide-react';
import Link from 'next/link';

export function EmptyState() {
    return (
        <motion.div
            variants={STAGGER_CONTAINER_VARIANTS}
            initial="hidden"
            animate="visible"
            className="w-full max-w-5xl space-y-10"
        >
            <motion.div variants={STAGGER_ITEM_VARIANTS} className="space-y-3 text-center">
                <FeatureBadge icon={Sparkles} className="mb-3" ariaLabel="Feature badge">
                    Get Started
                </FeatureBadge>
                <h3 className="text-3xl font-semibold tracking-tight">No playlists yet</h3>
                <p className="text-base text-muted-foreground">
                    Get started with a mood card or jump straight into a custom prompt—your first mix is just a click away.
                </p>
            </motion.div>

            <motion.div variants={STAGGER_ITEM_VARIANTS} className="space-y-4">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-muted-foreground text-center">
                    Mood jump-starts
                </p>
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                >
                    <SampleMoods
                        requireAuth={false}
                        showHeader={false}
                        maxCards={6}
                        containerClassName="overflow-visible p-0"
                        contentClassName="mx-auto max-w-4xl px-0 pb-0 pt-0"
                        gridClassName="mt-0 gap-5 sm:grid-cols-2 lg:grid-cols-3"
                        cardClassName="h-64 w-full"
                        showAllOnMobile
                    />
                </motion.div>
            </motion.div>

            <motion.div
                variants={STAGGER_ITEM_VARIANTS}
                className="flex justify-center"
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                        ...SPRING_TRANSITIONS.gentle,
                        delay: 0.6,
                    }}
                    {...BUTTON_MOTION_PROPS}
                >
                    <Link href="/create" prefetch={false} className="inline-flex">
                        <Button size="lg">✨ Create Custom Playlist</Button>
                    </Link>
                </motion.div>
            </motion.div>
        </motion.div>
    );
}
