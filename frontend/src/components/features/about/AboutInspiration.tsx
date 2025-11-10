'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Lightbulb } from 'lucide-react';

export function AboutInspiration() {
    return (
        <motion.section
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
        >
            <motion.div
                className="flex items-center gap-3 mb-6"
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: 0.1, ease: 'easeOut' }}
            >
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/10">
                    <Lightbulb className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">The Inspiration</h2>
            </motion.div>
            <div className="space-y-4 text-base leading-relaxed">
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.2, ease: 'easeOut' }}
                >
                    Remember that Spotify feature that could create a playlist from another playlist? I used to rely on it
                    heavily for music discovery—finding interesting songs to add to my own collections.
                </motion.p>
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.3, ease: 'easeOut' }}
                >
                    The idea for MoodList is simple: <strong className="text-foreground">just describe what you want,
                        and get a solid playlist out of it.</strong> No manual searching, no endless scrolling. Just a query
                    and boom—curated music that&apos;s listenable by you on Spotify.
                </motion.p>
            </div>
        </motion.section>
    );
}
