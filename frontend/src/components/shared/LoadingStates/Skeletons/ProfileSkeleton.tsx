import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { RecentActivitySkeleton } from './RecentActivitySkeleton';

export function ProfileSkeleton() {
    return (
        <div className="h-screen pt-2 sm:pt-3 px-2 sm:px-3 overflow-hidden">
            <div className="h-full max-w-7xl mx-auto flex flex-col">
                {/* Compact Header */}
                <div className="flex items-center justify-between mb-2 sm:mb-3">
                    <div className="min-w-0">
                        <Skeleton className="h-4 sm:h-5 w-24 sm:w-32 mb-1" />
                        <Skeleton className="h-3 w-32 sm:w-40 hidden sm:block" />
                    </div>
                    <div className="hidden sm:flex gap-3">
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-4 w-12" />
                    </div>
                </div>

                {/* Compact Stats */}
                <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-2 sm:mb-3 flex-shrink-0">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Card key={i} className="p-2 sm:p-3">
                            <div className="flex items-center gap-2 sm:gap-3">
                                <Skeleton className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex-shrink-0" />
                                <div className="min-w-0 flex-1">
                                    <Skeleton className="hidden sm:block h-3 w-12 sm:w-16 mb-1" />
                                    <Skeleton className="h-5 sm:h-6 w-6 sm:w-10" />
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>

                {/* Dashboard Grid */}
                <div className="flex-shrink-0 grid grid-cols-1 lg:grid-cols-3 gap-2 sm:gap-3 overflow-hidden min-h-0">
                    {/* Mobile: Scrollable */}
                    <div className="lg:hidden overflow-y-auto min-h-0 space-y-2 sm:space-y-3">
                        <Card>
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-28" />
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <Skeleton key={i} className="h-12 w-full" />
                                ))}
                            </CardContent>
                        </Card>

                        <RecentActivitySkeleton />

                        <Card>
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-28" />
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <div key={i} className="space-y-1">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-2 w-full rounded-full" />
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Desktop: Left Column */}
                    <div className="hidden lg:flex lg:col-span-2 flex-col gap-3">
                        <div className="flex-1 min-h-0">
                            <RecentActivitySkeleton />
                        </div>

                        <Card>
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-32" />
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-2">
                                    {Array.from({ length: 3 }).map((_, i) => (
                                        <Skeleton key={i} className="h-20" />
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Desktop: Right Column */}
                    <div className="hidden lg:flex flex-col gap-3">
                        <Card>
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-28" />
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <Skeleton key={i} className="h-12 w-full" />
                                ))}
                            </CardContent>
                        </Card>

                        <Card className="flex-1">
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-28" />
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <div key={i} className="space-y-1">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-2 w-full rounded-full" />
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}
