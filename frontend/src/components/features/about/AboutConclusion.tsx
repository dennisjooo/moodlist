'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Award } from 'lucide-react';

export function AboutConclusion() {
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
                    <Award className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">The Bottom Line</h2>
            </motion.div>
            <div className="space-y-4 text-base leading-relaxed">
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.2, ease: 'easeOut' }}
                >
                    It&apos;s not the best. It&apos;s not the cleanest. But it&apos;s <em>something</em>—something
                    I built from scratch, something that works, and something I can put in my portfolio.
                </motion.p>
                <motion.p
                    className="text-muted-foreground"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.3, ease: 'easeOut' }}
                >
                    Most importantly: it was fun. I learned a ton, broke things, fixed them (mostly), and came out
                    the other side with a working product.
                </motion.p>
                <motion.p
                    className="text-muted-foreground/70 italic text-lg mt-8 pt-8 border-t border-border/40"
                    initial={{ opacity: 0, y: 12 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-80px' }}
                    transition={{ duration: 0.4, delay: 0.4, ease: 'easeOut' }}
                >
                    If you find some cool music along the way, that&apos;s just a bonus.
                </motion.p>
            </div>
        </motion.section>
    );
}
