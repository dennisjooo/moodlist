'use client';

import { motion } from '@/components/ui/lazy-motion';
import { Github, Linkedin } from 'lucide-react';

export function AboutFooter() {
    return (
        <>
            {/* Signature */}
            <motion.div
                className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
            >
                <div className="text-center">
                    <p className="text-muted-foreground italic">- with love Dennis</p>
                </div>
            </motion.div>

            {/* Footer */}
            <motion.footer
                className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pb-8"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.5, delay: 0.1, ease: 'easeOut' }}
            >
                <div className="border-t border-border/40 pt-8">
                    <div className="flex items-center justify-center gap-6 text-muted-foreground">
                        <div className="flex items-center gap-2">
                            <Github size={16} />
                            <a
                                href="https://github.com/dennisjooo"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:text-primary transition-colors"
                            >
                                dennisjooo
                            </a>
                        </div>
                        <div className="flex items-center gap-2">
                            <Linkedin size={16} />
                            <a
                                href="https://www.linkedin.com/in/dennisjooo/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:text-primary transition-colors"
                            >
                                dennisjooo
                            </a>
                        </div>
                    </div>
                </div>
            </motion.footer>
        </>
    );
}
