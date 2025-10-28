import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function MoodInputSkeleton() {
    return (
        <Card className="w-full border-0 shadow-lg">
            <CardContent className="p-6">
                <div className="space-y-4">
                    {/* Textarea skeleton */}
                    <Skeleton className="min-h-[120px] w-full" />

                    {/* Example buttons skeleton */}
                    <div className="flex flex-wrap gap-1.5 justify-center sm:justify-start">
                        {[80, 100, 90, 85, 95, 90].map((width, i) => (
                            <Skeleton
                                key={i}
                                className="h-7"
                                style={{ width: `${width}px` }}
                            />
                        ))}
                    </div>

                    {/* Button skeleton */}
                    <Skeleton className="w-full h-9" />
                </div>
            </CardContent>
        </Card>
    );
}

