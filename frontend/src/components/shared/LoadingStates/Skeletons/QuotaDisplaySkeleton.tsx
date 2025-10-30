import { Skeleton } from '@/components/ui/skeleton';

interface QuotaDisplaySkeletonProps {
    className?: string;
}

export function QuotaDisplaySkeleton({ className = '' }: QuotaDisplaySkeletonProps) {
    return (
        <div className={className}>
            <div className="rounded-2xl border border-border/40 bg-background/80 p-3 shadow-[0_18px_40px_-25px_rgba(15,23,42,0.4)] backdrop-blur-xl">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                        <div className="mb-0.5 flex items-center gap-2">
                            <Skeleton className="h-3 w-3 rounded-full" />
                            <Skeleton className="h-3 w-20" />
                        </div>
                        <Skeleton className="h-3 w-full mt-1.5" />
                    </div>
                    <div className="text-right">
                        <Skeleton className="h-5 w-12" />
                    </div>
                </div>
                {/* Progress bar skeleton */}
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted/60">
                    <Skeleton className="h-full w-0" />
                </div>
            </div>
        </div>
    );
}

