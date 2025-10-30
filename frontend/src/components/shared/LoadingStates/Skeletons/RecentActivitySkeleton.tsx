import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock } from 'lucide-react';

export function RecentActivitySkeleton() {
    return (
        <Card className="lg:h-full flex flex-col">
            <CardHeader className="flex-shrink-0 pb-3">
                <CardTitle className="flex items-center space-x-2 text-base">
                    <Clock className="w-4 h-4" />
                    <span>Recent Activity</span>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {Array.from({ length: 2 }).map((_, i) => (
                        <div key={i} className="flex gap-4 pb-4 border-b last:border-b-0 last:pb-0">
                            <Skeleton className="w-10 h-10 rounded-full flex-shrink-0" />
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-4 w-32" />
                                    <Skeleton className="h-5 w-16" />
                                </div>
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-3/4" />
                                <div className="flex items-center gap-3">
                                    <Skeleton className="h-3 w-16" />
                                    <Skeleton className="h-3 w-20" />
                                    <Skeleton className="h-3 w-12 ml-auto" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
