import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft } from 'lucide-react';

export function ProfileSkeleton() {
    return (
        <div className="h-screen bg-gradient-to-br from-background to-muted p-2 sm:p-3 overflow-hidden">
            <div className="h-full max-w-7xl mx-auto flex flex-col">
                {/* Compact Header */}
                <div className="flex items-center justify-between mb-2 sm:mb-3">
                    <div className="flex items-center space-x-2 sm:space-x-3 min-w-0">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled>
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <div className="flex items-center space-x-2 min-w-0">
                            <Skeleton className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex-shrink-0" />
                            <div className="min-w-0">
                                <Skeleton className="h-4 sm:h-5 w-24 sm:w-32 mb-1" />
                                <Skeleton className="h-3 w-16 sm:w-20 hidden sm:block" />
                            </div>
                        </div>
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
                            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-1 sm:gap-2">
                                <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
                                <div className="min-w-0 text-center sm:text-left">
                                    <Skeleton className="h-3 w-12 sm:w-16 mb-1 mx-auto sm:mx-0" />
                                    <Skeleton className="h-5 sm:h-6 w-8 sm:w-12 mx-auto sm:mx-0" />
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>

                {/* Dashboard Grid */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-2 sm:gap-3 overflow-hidden min-h-0">
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

                        <Card>
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-32" />
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <div key={i} className="flex gap-3">
                                        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
                                        <div className="flex-1 space-y-2">
                                            <Skeleton className="h-4 w-3/4" />
                                            <Skeleton className="h-3 w-full" />
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>

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
                        <Card className="flex-1">
                            <CardHeader className="pb-3">
                                <Skeleton className="h-5 w-32" />
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <div key={i} className="flex gap-3">
                                        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
                                        <div className="flex-1 space-y-2">
                                            <Skeleton className="h-4 w-3/4" />
                                            <Skeleton className="h-3 w-full" />
                                            <Skeleton className="h-3 w-1/2" />
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>

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
