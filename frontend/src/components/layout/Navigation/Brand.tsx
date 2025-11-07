'use client';

import { Badge } from '@/components/ui/badge';
import { Logo } from './Logo';
import Link from 'next/link';

interface BrandProps {
    href?: string;
}

export function Brand({ href = '/' }: BrandProps) {
    return (
        <Link
            href={href}
            className="flex items-center gap-2.5 group"
            aria-label="MoodList Home"
        >
            <Logo className="group-hover:shadow-md transition-all duration-300 ease-out group-hover:scale-[1.02] group-active:scale-[0.98]" />
            <div className="flex items-center gap-2">
                <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent transition-all duration-200 group-hover:from-foreground group-hover:via-foreground group-hover:to-foreground/90">
                    MoodList
                </span>
                <Badge
                    variant="secondary"
                    className="text-[10px] font-semibold px-1.5 py-0 h-4"
                >
                    BETA
                </Badge>
            </div>
        </Link>
    );
}
