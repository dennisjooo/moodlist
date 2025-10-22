import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { motion } from 'framer-motion';
import { Music } from 'lucide-react';

export function PlaylistGridSkeleton() {
    return (
        <>
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-center mb-12"
            >
                <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto mb-6">
                    <Music className="w-4 h-4" />
                    Your Music History
                </Badge>

                <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-4">
                    My Playlists
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                    All your mood-based playlists in one place. Relive your musical moments.
                </p>
            </motion.div>

            {/* Grid skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => (
                    <Card key={i} className="overflow-hidden">
                        <CardHeader className="p-0">
                            <Skeleton className="h-32 w-full rounded-none" />
                        </CardHeader>
                        <CardContent className="p-4 space-y-3">
                            <div className="space-y-2">
                                <Skeleton className="h-6 w-3/4" />
                                <Skeleton className="h-4 w-full" />
                            </div>
                            <div className="flex items-center gap-4 pt-2">
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-4 w-20" />
                            </div>
                            <div className="flex gap-2 pt-2">
                                <Skeleton className="h-6 w-16" />
                                <Skeleton className="h-6 w-20" />
                            </div>
                            <div className="flex gap-2 pt-2">
                                <Skeleton className="h-9 flex-1" />
                                <Skeleton className="h-9 w-20" />
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </>
    );
}

