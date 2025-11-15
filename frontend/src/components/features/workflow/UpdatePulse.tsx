'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface UpdatePulseProps {
    triggerKey?: string | number;
    className?: string;
}

/**
 * Visual indicator that pulses when new data arrives.
 * Gives users confidence that progress is being made.
 */
export function UpdatePulse({ triggerKey, className = '' }: UpdatePulseProps) {
    const [isPulsing, setIsPulsing] = useState(false);

    useEffect(() => {
        if (triggerKey !== undefined) {
            setIsPulsing(true);
            const timer = setTimeout(() => setIsPulsing(false), 800);
            return () => clearTimeout(timer);
        }
    }, [triggerKey]);

    return (
        <div className={cn('relative inline-flex items-center', className)}>
            <div
                className={cn(
                    'h-2 w-2 rounded-full bg-green-500 transition-all duration-300',
                    isPulsing && 'scale-125'
                )}
            />
            {isPulsing && (
                <>
                    <span className="absolute h-2 w-2 rounded-full bg-green-500 animate-ping opacity-75" />
                    <span className="absolute h-3 w-3 rounded-full bg-green-400 animate-ping opacity-40" />
                </>
            )}
        </div>
    );
}
