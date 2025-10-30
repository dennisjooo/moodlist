import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Sparkles } from 'lucide-react';

export function WorkflowProgressSkeleton() {
    return (
        <div className="space-y-6">
            <div className="space-y-3 text-center">
                <Badge
                    variant="outline"
                    className="mx-auto flex w-fit items-center gap-2 rounded-full border-border/60 bg-background/80 px-4 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground/80 backdrop-blur"
                >
                    <Sparkles className="h-4 w-4" />
                    AI-Powered Playlist Creation
                </Badge>

                <div className="space-y-1">
                    <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                        Crafting your playlist
                    </h1>
                    <p className="mx-auto max-w-2xl text-sm text-muted-foreground">
                        We are weaving together tracks that match the feeling you shared. Hang tight while the mix comes to life.
                    </p>
                </div>
            </div>

            <Card className="w-full overflow-hidden">
                <CardHeader className="pb-2 overflow-hidden">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Skeleton className="h-5 w-5 rounded-full" />
                            <Skeleton className="h-6 w-48" />
                        </CardTitle>
                        <Skeleton className="h-9 w-20" />
                    </div>
                </CardHeader>

                <CardContent className="space-y-3 overflow-hidden">
                    <div className="space-y-3">
                        <Skeleton className="h-4 w-full" />
                        <div className="flex gap-2">
                            <Skeleton className="h-2 flex-1" />
                            <Skeleton className="h-2 flex-1" />
                            <Skeleton className="h-2 flex-1" />
                        </div>
                        <div className="space-y-2 pt-2">
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-4 w-1/2" />
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

