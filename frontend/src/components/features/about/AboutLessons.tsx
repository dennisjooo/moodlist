'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Target } from 'lucide-react';

export function AboutLessons() {
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
                    <Target className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">What I Learned</h2>
            </motion.div>
            <div className="space-y-4 text-base leading-relaxed">
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.2, ease: 'easeOut' }}
                >
                    <strong className="text-foreground">End-to-end development is hard.</strong> Like, really hard.
                    Full respect to everyone who does this on the daily. Juggling frontend, backend, databases, APIs,
                    caching, authentication, deployment is a lot to ask of oneself.
                </motion.p>
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.3, ease: 'easeOut' }}
                >
                    This project taught me more about the reality of building production systems than any tutorial
                    ever could. The messy parts, the debugging sessions, the tradeoffs, the compromises—that&apos;s
                    where the real learning happens.
                </motion.p>
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.4, ease: 'easeOut' }}
                >
                    In all honesty, it&apos;s been a fun exercise. I used Cursor and Kilo along the way to help—it&apos;s
                    cheating sure, but it made life a lot easier and for a funsies project, why the fuck not? AI code
                    editors are not a sin, they&apos;re tools to help you get shit done.
                </motion.p>
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.5, ease: 'easeOut' }}
                >
                    I also learned that breaking things into smaller parts and making them incrementally is a
                    lot easier than trying to do it all at once. I find it hard and intimidating to start this project as
                    it was difficult to find a place to start from, but once you have the ball rolling, it&apos;s a lot easier to keep going.
                </motion.p>
            </div>
        </motion.section>
    );
}
