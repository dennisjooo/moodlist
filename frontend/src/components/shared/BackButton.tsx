'use client';

import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BackButtonProps {
    onClick?: () => void;
    disabled?: boolean;
    children?: React.ReactNode;
    className?: string;
    variant?: 'default' | 'ghost';
    animated?: boolean;
    size?: 'default' | 'sm' | 'lg' | 'icon';
    iconOnly?: boolean;
}

export function BackButton({
    onClick,
    disabled = false,
    children = 'Back',
    className,
    variant = 'ghost',
    animated = false,
    size,
    iconOnly = false,
}: BackButtonProps) {
    // Determine icon size based on button size
    const iconSizeClass = size === 'sm' ? 'w-4 h-4 sm:w-5 sm:h-5' : 'w-4 h-4';
    
    return (
        <Button
            variant={variant}
            size={size}
            onClick={onClick}
            disabled={disabled}
            className={cn(
                !iconOnly && 'gap-2',
                animated && 'hover:gap-3 transition-all group animate-in fade-in slide-in-from-left-4 duration-500',
                className
            )}
        >
            <ArrowLeft className={cn(
                iconSizeClass,
                animated && 'group-hover:-translate-x-1 transition-transform'
            )} />
            {!iconOnly && children}
        </Button>
    );
}

