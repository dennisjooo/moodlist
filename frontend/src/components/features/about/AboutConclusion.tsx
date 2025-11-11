'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Award } from 'lucide-react';

export function AboutConclusion() {
    return (
        <motion.section
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
        >
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/10">
                    <Award className="w-4 h-4 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground">The Bottom Line</h2>
            </div>
            <div className="space-y-4 text-base leading-relaxed">
                <p className="text-muted-foreground">
                    It&apos;s not the best. It&apos;s not the cleanest. But it&apos;s <em>something</em>—something
                    I built from scratch, something that works, and something I can put in my portfolio.
                </p>
                <p className="text-muted-foreground">
                    Most importantly: it was fun. I learned a ton, broke things, fixed them (mostly), and came out
                    the other side with a working product.
                </p>
                <p className="text-muted-foreground/70 italic text-lg mt-8 pt-8 border-t border-border/40">
                    If you find some cool music along the way, that&apos;s just a bonus.
                </p>
            </div>
        </motion.section>
    );
}
