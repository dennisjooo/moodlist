import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export function WorkflowProgressSkeleton() {
    return (
        <Card
            className={cn(
                'w-full overflow-hidden transition-all duration-300',
                'border-border/60 shadow-sm',
                'bg-gradient-to-br from-card via-card to-card/95'
            )}
        >
            {/* Header matching SessionHeader */}
            <CardHeader className="pb-4 border-b border-border/40 bg-gradient-to-r from-muted/20 to-transparent space-y-3">
                {/* Session header skeleton */}
                <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-base flex items-center gap-2.5 font-semibold">
                        <Skeleton className="h-5 w-5 rounded-full" />
                        <Skeleton className="h-6 w-48" />
                    </CardTitle>
                    <Skeleton className="h-9 w-20" />
                </div>

                {/* Status section skeleton */}
                <div className="space-y-3">
                    {/* Status message */}
                    <Skeleton className="h-4 w-full max-w-md" />

                    {/* Progress timeline */}
                    <div className="flex gap-2">
                        <Skeleton className="h-2 flex-1" />
                        <Skeleton className="h-2 flex-1" />
                        <Skeleton className="h-2 flex-1" />
                        <Skeleton className="h-2 flex-1" />
                    </div>
                </div>
            </CardHeader>

            {/* Content matching CardContent layout */}
            <CardContent className="pt-4">
                <div className="grid gap-6 lg:grid-cols-2">
                    {/* Left panel - MoodAnalysis & Insights */}
                    <div className="space-y-4">
                        {/* Mood analysis skeleton */}
                        <div className="space-y-3 p-4 rounded-lg border border-border/40 bg-muted/30">
                            <Skeleton className="h-5 w-32" />
                            <div className="space-y-2">
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-3/4" />
                            </div>
                        </div>

                        {/* Workflow insights skeleton */}
                        <div className="space-y-2">
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-2/3" />
                        </div>
                    </div>

                    {/* Right panel - Tracks */}
                    <div className="lg:border-l lg:border-border/30 lg:pl-6">
                        <div className="flex flex-col h-full">
                            {/* Tracks header */}
                            <div className="flex items-center justify-between gap-3 px-1 pb-3">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-4 w-4 rounded-full" />
                                    <Skeleton className="h-5 w-24" />
                                </div>
                                <Skeleton className="h-6 w-16" />
                            </div>

                            {/* Track list skeleton */}
                            <div className="space-y-2 p-2 pr-4">
                                {[...Array(3)].map((_, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-3 p-3 rounded-lg border border-border/40 bg-muted/20"
                                    >
                                        <Skeleton className="h-12 w-12 rounded" />
                                        <div className="flex-1 space-y-2">
                                            <Skeleton className="h-4 w-3/4" />
                                            <Skeleton className="h-3 w-1/2" />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Footer */}
                            <div className="flex items-center justify-center gap-2 pt-3">
                                <Skeleton className="h-2 w-2 rounded-full" />
                                <Skeleton className="h-3 w-32" />
                            </div>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

