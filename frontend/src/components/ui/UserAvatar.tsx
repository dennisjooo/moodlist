'use client';

import { motion } from '@/components/ui/lazy-motion';
import type { User as UserType } from '@/lib/types/auth';
import { cn } from '@/lib/utils';
import { User } from 'lucide-react';
import Image from 'next/image';

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

const ICON_SIZES = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-6 h-6',
} as const;

export function UserAvatar({ user, size = 'md', withMotion = false, className }: UserAvatarProps) {
    const sizeClass = AVATAR_SIZES[size];
    const iconSize = ICON_SIZES[size];

    const avatarContent = user.profile_image_url ? (
        <Image
            src={user.profile_image_url}
            alt={user.display_name}
            width={size === 'sm' ? 24 : size === 'md' ? 32 : 48}
            height={size === 'sm' ? 24 : size === 'md' ? 32 : 48}
            className={cn(
                sizeClass,
                'rounded-full ring-2 ring-primary/20 hover:ring-primary/40 transition-all',
                className
            )}
        />
    ) : (
        <div
            className={cn(
                sizeClass,
                'bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center ring-2 ring-primary/20',
                className
            )}
        >
            <User className={cn(iconSize, 'text-primary')} />
        </div>
    );

    if (withMotion && user.profile_image_url) {
        return (
            <motion.div
                whileHover={{ scale: 1.1 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
                {avatarContent}
            </motion.div>
        );
    }

    return avatarContent;
}
