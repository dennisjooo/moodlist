import { Skeleton } from '@/components/ui/skeleton';

export const TrackDetailsLoadingSkeleton = () => (
    <div className="space-y-2 p-3">
        <div className="space-y-0.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
        </div>
        <div className="border-t border-border/50" />
        <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0 space-y-1.5">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
                <Skeleton className="h-3 w-1/2" />
                <Skeleton className="h-3 w-3/4" />
            </div>
            <Skeleton className="w-20 h-20 rounded-md flex-shrink-0" />
        </div>
        <div className="border-t border-border/50 pt-2">
            <Skeleton className="h-8 w-full rounded-md" />
        </div>
    </div>
);

