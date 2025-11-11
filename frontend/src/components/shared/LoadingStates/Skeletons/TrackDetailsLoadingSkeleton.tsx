import { Skeleton } from '@/components/ui/skeleton';

export const TrackDetailsLoadingSkeleton = () => (
    <div className="relative w-[280px] h-[280px]">
        {/* Album art skeleton */}
        <Skeleton className="w-full h-full rounded-[15px]" />

        {/* Text overlay skeleton */}
        <div className="absolute inset-0 flex flex-col justify-end p-4 space-y-1.5">
            <Skeleton className="h-4 w-3/4 bg-white/20" />
            <Skeleton className="h-3 w-1/2 bg-white/15" />
            <Skeleton className="h-3 w-2/3 bg-white/15" />
            <div className="pt-2 flex justify-center">
                <Skeleton className="h-3 w-24 bg-white/10" />
            </div>
        </div>
    </div>
);

