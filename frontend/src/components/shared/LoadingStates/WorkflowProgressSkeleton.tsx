import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Sparkles } from 'lucide-react';

export function WorkflowProgressSkeleton() {
    return (
        <>
            <div className="text-center mb-12">
                <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                    <Sparkles className="w-4 h-4" />
                    AI-Powered Playlist Creation
                </Badge>

                <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                    Creating your playlist
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                    Our AI is working on creating the perfect Spotify playlist for your mood.
                </p>
            </div>

            <Card className="w-full">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Skeleton className="w-5 h-5 rounded-full" />
                            <Skeleton className="h-6 w-48" />
                        </div>
                        <Skeleton className="h-9 w-20" />
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
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
                </CardContent>
            </Card>
        </>
    );
}

