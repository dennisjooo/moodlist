'use client';

import { Badge } from '@/components/ui/badge';
import { Music } from 'lucide-react';
import Link from 'next/link';

interface BrandProps {
    href?: string;
}

export function Brand({ href = '/' }: BrandProps) {
    return (
        <Link href={href} className="flex items-center space-x-3 group">
            <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary/80 rounded-lg flex items-center justify-center shadow-md group-hover:shadow-lg transition-all duration-200 group-hover:scale-105 group-hover:rotate-[5deg] group-active:scale-95">
                <Music className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text transition-opacity duration-200 group-hover:opacity-90">
                MoodList
            </span>
            <Badge
                variant="secondary"
                className="ml-2 text-xs font-semibold px-2 py-0.5 bg-primary/10 text-primary border-primary/20"
            >
                Beta
            </Badge>
        </Link>
    );
}
