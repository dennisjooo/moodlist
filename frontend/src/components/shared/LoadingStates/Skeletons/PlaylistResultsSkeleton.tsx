import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function PlaylistResultsSkeleton() {
    return (
        <div className="space-y-6">
            {/* Status Banner Skeleton */}
            <Card className="relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-orange-500 to-amber-500" />
                <CardContent className="p-4 sm:p-6">
                    <div className="flex flex-col sm:flex-row gap-4">
                        {/* Left side: Icon + Info */}
                        <div className="flex gap-3 sm:gap-4 flex-1 min-w-0">
                            <Skeleton className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl flex-shrink-0" />
                            <div className="flex-1 min-w-0 flex flex-col justify-center space-y-2">
                                <Skeleton className="h-6 sm:h-7 w-48" />
                                <div className="flex items-start gap-1.5">
                                    <Skeleton className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                    <Skeleton className="h-4 w-full max-w-xs" />
                                </div>
                                <Skeleton className="h-3 w-32 ml-5" />
                            </div>
                        </div>

                        {/* Right side: Actions */}
                        <div className="flex flex-col gap-2 sm:justify-center sm:min-w-[200px]">
                            <Skeleton className="h-11 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Mood Analysis Card Skeleton */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between gap-4">
                        <Skeleton className="h-6 w-32" />
                        <Skeleton className="h-7 w-16 rounded-md" />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-3/4" />
                        <div className="flex gap-2">
                            <Skeleton className="h-6 w-16" />
                            <Skeleton className="h-6 w-20" />
                            <Skeleton className="h-6 w-14" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Track List Skeleton */}
            <Card>
                <CardHeader>
                    <Skeleton className="h-6 w-48" />
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {/* Track rows */}
                        {Array.from({ length: 8 }).map((_, i) => (
                            <div key={i} className="flex items-center gap-3 p-2.5">
                                <Skeleton className="w-7 h-7 rounded-full" />
                                <div className="flex-1 space-y-1">
                                    <Skeleton className="h-4 w-3/4" />
                                    <Skeleton className="h-3 w-1/2" />
                                </div>
                                <div className="flex items-center gap-2">
                                    <Skeleton className="w-12 h-4" />
                                    <Skeleton className="w-8 h-8 rounded-full" />
                                    <Skeleton className="w-8 h-8 rounded-full" />
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Actions Skeleton */}
            <div className="flex gap-3">
                <Skeleton className="h-10 flex-1" />
            </div>
        </div>
    );
}

