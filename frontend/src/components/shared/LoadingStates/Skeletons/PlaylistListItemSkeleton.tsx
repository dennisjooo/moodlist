import { Skeleton } from '@/components/ui/skeleton';

export function PlaylistListItemSkeleton() {
    return (
        <div className="rounded-2xl border border-border/40 bg-card/50 backdrop-blur-sm shadow-sm p-4 sm:p-5 md:p-6">
            <div className="flex flex-col gap-4 sm:gap-5 md:flex-row md:items-center md:justify-between md:gap-6">
                {/* Left side - Content */}
                <div className="flex min-w-0 flex-1 items-start gap-3 sm:gap-4 md:gap-5">
                    {/* Thumbnail */}
                    <Skeleton className="h-16 w-16 shrink-0 rounded-xl sm:h-20 sm:w-20 sm:rounded-2xl md:h-24 md:w-24" />

                    {/* Text content */}
                    <div className="min-w-0 flex-1 space-y-2 sm:space-y-2.5 md:space-y-3 md:pt-1">
                        <div>
                            <Skeleton className="h-5 w-3/4 mb-1.5 sm:h-6 sm:mb-2 md:h-7" />
                            <Skeleton className="h-4 w-full sm:h-4" />
                            <Skeleton className="h-4 w-2/3 mt-1 sm:h-4" />
                        </div>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 sm:gap-x-4 sm:gap-y-2 md:gap-x-5">
                            <Skeleton className="h-3 w-24 sm:h-3.5 sm:w-28" />
                            <Skeleton className="h-3 w-20 sm:h-3.5 sm:w-24" />
                        </div>
                    </div>
                </div>

                {/* Right side - Status & Actions */}
                <div className="flex shrink-0 flex-row items-end justify-between gap-3 border-t border-border/30 pt-3 sm:border-t-0 sm:pt-0 md:min-w-[140px] md:flex-col md:border-l md:border-t-0 md:pl-6 md:pt-0">
                    <Skeleton className="h-6 w-20 sm:h-7 sm:w-24" />
                    
                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <Skeleton className="h-8 w-16 sm:h-9 sm:w-20" />
                        <Skeleton className="h-8 w-8 sm:h-9 sm:w-9" />
                        <Skeleton className="h-8 w-8 sm:h-9 sm:w-9" />
                    </div>
                </div>
            </div>
        </div>
    );
}

export function PlaylistListSkeleton() {
    return (
        <div className="space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
                <PlaylistListItemSkeleton key={i} />
            ))}
        </div>
    );
}

