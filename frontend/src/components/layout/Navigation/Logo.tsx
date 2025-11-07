import { AudioLines } from 'lucide-react';

interface LogoProps {
    className?: string;
    size?: 'sm' | 'md' | 'lg';
}

const sizeMap = {
    sm: {
        container: 'w-7 h-7',
        icon: 'w-4 h-4',
    },
    md: {
        container: 'w-9 h-9',
        icon: 'w-5 h-5',
    },
    lg: {
        container: 'w-12 h-12',
        icon: 'w-7 h-7',
    },
};

export function Logo({ className = '', size = 'md' }: LogoProps) {
    const { container, icon } = sizeMap[size];

    return (
        <div
            className={`relative ${container} bg-gradient-to-br from-foreground via-foreground to-foreground/90 rounded-xl flex items-center justify-center shadow-sm ${className}`}
        >
            <div className="absolute inset-0 bg-gradient-to-tr from-white/0 dark:from-white/0 to-white/10 dark:to-white/5 rounded-xl" />
            <AudioLines className={`${icon} text-background relative z-10`} strokeWidth={2.5} />
        </div>
    );
}
