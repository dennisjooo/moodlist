import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Music, User } from 'lucide-react';

export function ProfileSkeleton() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted p-4">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-6">
                    <Button variant="ghost" className="mb-4" disabled>
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Back
                    </Button>

                    <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center">
                            <Music className="w-6 h-6 text-primary-foreground" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold">Profile</h1>
                            <p className="text-muted-foreground">Your connected Spotify account</p>
                        </div>
                    </div>
                </div>

                {/* Profile Card */}
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                            <User className="w-5 h-5" />
                            <span>Profile Information</span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col md:flex-row gap-6">
                            {/* Profile Picture Skeleton */}
                            <div className="flex-shrink-0">
                                <Skeleton className="w-[120px] h-[120px] rounded-full" />
                            </div>

                            {/* Profile Details Skeleton */}
                            <div className="flex-1 space-y-4">
                                <div>
                                    <Skeleton className="h-8 w-48 mb-2" />
                                    <Skeleton className="h-5 w-32" />
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <Skeleton className="h-5 w-full" />
                                    <Skeleton className="h-5 w-full" />
                                    <Skeleton className="h-5 w-full" />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* App Usage Metrics Cards Skeleton */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Card key={i}>
                            <CardContent className="pt-6">
                                <div className="text-center">
                                    <Skeleton className="w-12 h-12 rounded-full mx-auto mb-3" />
                                    <Skeleton className="h-5 w-32 mx-auto mb-2" />
                                    <Skeleton className="h-8 w-16 mx-auto mb-1" />
                                    <Skeleton className="h-4 w-24 mx-auto" />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        </div>
    );
}

