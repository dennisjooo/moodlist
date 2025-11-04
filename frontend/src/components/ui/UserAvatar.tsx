'use client';

import type { User as UserType } from '@/lib/types/auth';
import { cn } from '@/lib/utils';
import { User } from 'lucide-react';
import Image from 'next/image';
import { useEffect, useState } from 'react';

interface UserAvatarProps {
    user: UserType;
    size?: 'sm' | 'md' | 'lg';
    withMotion?: boolean;
    className?: string;
}

const AVATAR_SIZES = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
} as const;

const SIZE_PX = {
    sm: 24,
    md: 32,
    lg: 48,
} as const;

const ICON_SIZES = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-6 h-6',
} as const;

const loadedImages = new Set<string>();

export function UserAvatar({ user, size = 'md', withMotion = false, className }: UserAvatarProps) {
    const src = user.profile_image_url;
    const [imageLoaded, setImageLoaded] = useState(() => Boolean(src && loadedImages.has(src)));
    const [imageError, setImageError] = useState(false);

    const sizeClass = AVATAR_SIZES[size];
    const iconSize = ICON_SIZES[size];
    const sizePx = SIZE_PX[size];
    const containerClasses = cn(
        sizeClass,
        'relative rounded-full ring-2 ring-primary/20 hover:ring-primary/40 transition-all',
        withMotion && 'transition-transform duration-200 hover:scale-110',
        className
    );

    useEffect(() => {
        if (!src) {
            setImageLoaded(false);
            setImageError(false);
            return;
        }

        const cached = loadedImages.has(src);
        setImageLoaded(cached);
        setImageError(false);
    }, [src]);

    const fallback = (
        <div
            className={cn(
                containerClasses,
                'bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center'
            )}
        >
            <User className={cn(iconSize, 'text-primary')} />
        </div>
    );

    if (!src || imageError) {
        return fallback;
    }

    // Wrapper to maintain consistent size and prevent layout shift
    return (
        <div className={containerClasses}>
            {/* Loading skeleton - fades out as image loads */}
            <div className={cn(
                'absolute inset-0 bg-accent/50 rounded-full transition-opacity duration-200 pointer-events-none',
                imageLoaded ? 'opacity-0' : 'opacity-100 animate-pulse'
            )} />

            <Image
                src={src}
                alt={user.display_name}
                width={sizePx}
                height={sizePx}
                className={cn(
                    'rounded-full object-cover relative z-10 transition-opacity duration-200',
                    imageLoaded ? 'opacity-100' : 'opacity-0'
                )}
                priority={size === 'md'} // Prioritize medium size (navigation)
                onLoadingComplete={() => {
                    if (src) {
                        loadedImages.add(src);
                    }
                    setImageLoaded(true);
                }}
                onError={() => {
                    if (src) {
                        loadedImages.delete(src);
                    }
                    setImageError(true);
                }}
            />
        </div>
    );
}
