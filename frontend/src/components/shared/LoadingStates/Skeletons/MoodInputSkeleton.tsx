import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function MoodInputSkeleton() {
    return (
        <div className="relative animate-in fade-in duration-300">
            <div
                aria-hidden="true"
                className="absolute inset-0 -z-10 rounded-3xl bg-gradient-to-br from-primary/30 via-primary/10 to-transparent opacity-70 blur-3xl"
            />
            <Card className="w-full overflow-hidden rounded-3xl border border-border/40 bg-background/80 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
                <CardContent className="p-5 sm:p-6">
                    <div className="space-y-4">
                        {/* Label skeleton */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Skeleton className="h-4 w-36" />
                                <Skeleton className="h-3 w-32" />
                            </div>
                            {/* Textarea skeleton */}
                            <Skeleton className="min-h-[100px] w-full rounded-2xl" />
                        </div>

                        {/* Preset section */}
                        <div className="space-y-2">
                            <Skeleton className="h-3 w-24" />
                            {/* Example buttons skeleton */}
                            <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                                {[80, 100, 90, 85, 95, 90].map((width, i) => (
                                    <Skeleton
                                        key={i}
                                        className="h-7 rounded-full"
                                        style={{ width: `${width}px` }}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Button skeleton */}
                        <Skeleton className="w-full h-10 rounded-full" />
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

