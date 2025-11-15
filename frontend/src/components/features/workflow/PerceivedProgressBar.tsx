'use client';

import { cn } from '@/lib/utils';
import { usePerceivedProgress } from './usePerceivedProgress';

interface PerceivedProgressBarProps {
    status: string | null;
    className?: string;
    showPercentage?: boolean;
}

/**
 * Progress bar that smoothly animates based on workflow stage.
 * Creates the perception of continuous forward progress.
 */
export function PerceivedProgressBar({
    status,
    className = '',
    showPercentage = false,
}: PerceivedProgressBarProps) {
    const { progress, percent } = usePerceivedProgress(status);
    const width = Math.max(progress * 100, percent);

    return (
        <div className={cn('space-y-1.5', className)}>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Processing</span>
                {showPercentage && <span className="font-medium">{percent}%</span>}
            </div>
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted/40">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-primary via-primary/90 to-primary/80 transition-all duration-500 ease-out"
                    style={{
                        width: `${width}%`,
                    }}
                />
            </div>
        </div>
    );
}
