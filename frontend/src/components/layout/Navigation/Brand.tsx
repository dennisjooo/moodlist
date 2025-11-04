'use client';

import { Badge } from '@/components/ui/badge';
import { motion } from '@/components/ui/lazy-motion';
import { SPRING_TRANSITIONS, SUBTLE_BUTTON_MOTION_PROPS } from '@/lib/constants/animations';
import { Music } from 'lucide-react';
import Link from 'next/link';

interface BrandProps {
    href?: string;
}

export function Brand({ href = '/' }: BrandProps) {
    return (
        <Link href={href} className="flex items-center space-x-3 group">
            <motion.div
                className="w-8 h-8 bg-gradient-to-br from-primary to-primary/80 rounded-lg flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow"
                whileHover={{ scale: 1.05, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
                transition={SPRING_TRANSITIONS.gentle}
            >
                <Music className="w-4 h-4 text-primary-foreground" />
            </motion.div>
            <motion.span
                className="font-bold text-xl bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text"
                {...SUBTLE_BUTTON_MOTION_PROPS}
                transition={SPRING_TRANSITIONS.gentle}
            >
                MoodList
            </motion.span>
            <Badge
                variant="secondary"
                className="ml-2 text-xs font-semibold px-2 py-0.5 bg-primary/10 text-primary border-primary/20"
            >
                Beta
            </Badge>
        </Link>
    );
}
