import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function PlaylistEditorSkeleton() {
    return (
        <div className="space-y-6">
            {/* Header Card Skeleton */}
            <Card>
                <CardHeader>
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-4 w-96 mt-2" />
                </CardHeader>
            </Card>

            {/* Two Column Layout Skeleton */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column - Search */}
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-32" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Skeleton className="h-10 w-full" />
                        <div className="space-y-2">
                            {Array.from({ length: 5 }).map((_, i) => (
                                <div key={i} className="flex items-center gap-3 p-2">
                                    <div className="flex-1 space-y-1">
                                        <Skeleton className="h-4 w-3/4" />
                                        <Skeleton className="h-3 w-1/2" />
                                    </div>
                                    <Skeleton className="h-8 w-16" />
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Right Column - Playlist */}
                <Card>
                    <CardHeader className="flex-row items-center justify-between">
                        <Skeleton className="h-6 w-40" />
                        <Skeleton className="h-9 w-20" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {Array.from({ length: 8 }).map((_, i) => (
                                <div key={i} className="flex items-center gap-3 p-2">
                                    <Skeleton className="w-6 h-6" />
                                    <div className="flex-1 space-y-1">
                                        <Skeleton className="h-4 w-3/4" />
                                        <Skeleton className="h-3 w-1/2" />
                                    </div>
                                    <Skeleton className="h-8 w-8" />
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Actions Skeleton */}
            <div className="flex gap-3">
                <Skeleton className="h-10 w-24" />
                <Skeleton className="h-10 flex-1" />
            </div>
        </div>
    );
}

