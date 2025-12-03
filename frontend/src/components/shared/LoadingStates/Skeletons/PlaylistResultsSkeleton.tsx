import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function PlaylistResultsSkeleton() {
    return (
        <div className="space-y-6">
            {/* Status Banner Skeleton */}
            <Card className="relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-orange-500 to-amber-500" />
                <CardContent className="p-6 sm:p-8">
                    <div className="flex flex-col md:flex-row gap-6 items-start">
                        {/* Icon */}
                        <div className="flex-shrink-0">
                            <Skeleton className="w-24 h-24 sm:w-32 sm:h-32 rounded-2xl" />
                        </div>

                        {/* Content Info */}
                        <div className="flex-1 min-w-0 space-y-3">
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-5 w-24 rounded-full" />
                                    <Skeleton className="h-4 w-16" />
                                </div>
                                <Skeleton className="h-8 sm:h-10 w-3/4" />
                                <Skeleton className="h-6 w-1/2" />
                            </div>
                            <Skeleton className="h-20 w-full max-w-2xl rounded-lg" />
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col gap-3 w-full md:w-auto md:min-w-[180px]">
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-12 w-full" />
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

