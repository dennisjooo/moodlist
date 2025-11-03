'use client';

import { RecentActivitySkeleton } from '@/components/shared/LoadingStates';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { RecentPlaylist } from '@/lib/api/user';
import { userAPI } from '@/lib/api/user';
import { cleanText } from '@/lib/utils/text';
import { CheckCircle, Clock, ExternalLink, Loader, Music, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

interface RecentActivityTimelineProps {
    recentActivity: RecentPlaylist[];
    enablePagination?: boolean;
    isLoading?: boolean;
}

const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'bg-green-500/10 text-green-600 border-green-200/50';
        case 'pending':
        case 'generating':
            return 'bg-blue-500/10 text-blue-600 border-blue-200/50';
        case 'failed':
            return 'bg-red-500/10 text-red-600 border-red-200/50';
        default:
            return 'bg-muted text-muted-foreground';
    }
};

const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
        case 'completed':
            return CheckCircle;
        case 'pending':
        case 'generating':
            return Loader;
        case 'failed':
            return XCircle;
        default:
            return Music;
    }
};

const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
};

export function RecentActivityTimeline({ recentActivity, enablePagination = false, isLoading: externalIsLoading = false }: RecentActivityTimelineProps) {
    const hasInitialActivities = recentActivity.length > 0;
    const [activities, setActivities] = useState<RecentPlaylist[]>(() => [...recentActivity]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasMore, setHasMore] = useState(enablePagination);
    const [offset, setOffset] = useState(() => enablePagination ? recentActivity.length : 0);
    const [isInitialLoad, setIsInitialLoad] = useState(() => enablePagination && !hasInitialActivities);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const displayedActivities = activities.length > 0 ? activities : recentActivity;
    const hasAnyActivities = displayedActivities.length > 0;
    const isFetching = externalIsLoading || (enablePagination && (isInitialLoad || isLoading));

    const loadMoreActivities = useCallback(async () => {
        if (isLoading || !hasMore || !enablePagination) return;

        setIsLoading(true);
        try {
            const newActivities = await userAPI.getUserPlaylists(20, offset);
            if (newActivities.length === 0) {
                setHasMore(false);
            } else {
                setActivities(prev => {
                    // Filter out duplicates by ID to prevent key conflicts
                    const existingIds = new Set(prev.map(activity => activity.id));
                    const uniqueNewActivities = newActivities.filter(activity => !existingIds.has(activity.id));
                    return [...prev, ...uniqueNewActivities];
                });
                setOffset(prev => prev + newActivities.length);
            }
        } catch (error) {
            console.error('Failed to load more activities:', error);
            setHasMore(false);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading, hasMore, offset, enablePagination]);

    const handleScroll = useCallback(() => {
        if (!scrollContainerRef.current || !enablePagination) return;

        const container = scrollContainerRef.current;
        const scrollTop = container.scrollTop;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;

        // Load more when user scrolls within 200px of the bottom
        if (scrollHeight - scrollTop - clientHeight < 200) {
            loadMoreActivities();
        }
    }, [loadMoreActivities, enablePagination]);

    // Load initial data when pagination is enabled
    useEffect(() => {
        if (enablePagination && isInitialLoad) {
            loadMoreActivities();
            setIsInitialLoad(false);
        }
    }, [enablePagination, isInitialLoad, loadMoreActivities]);

    // Update activities when recentActivity prop changes
    useEffect(() => {
        if (enablePagination) {
            setActivities(prev => {
                const recentIds = new Set(recentActivity.map(activity => activity.id));
                const mergedActivities = [...recentActivity];

                for (const activity of prev) {
                    if (!recentIds.has(activity.id)) {
                        mergedActivities.push(activity);
                    }
                }

                return mergedActivities;
            });

            if (recentActivity.length > 0) {
                setIsInitialLoad(false);
            }

            setOffset(prev => Math.max(prev, recentActivity.length));
        } else {
            setActivities([...recentActivity]);
        }
    }, [recentActivity, enablePagination]);

    useEffect(() => {
        const container = scrollContainerRef.current;
        if (container && enablePagination) {
            container.addEventListener('scroll', handleScroll);
            return () => container.removeEventListener('scroll', handleScroll);
        }
    }, [handleScroll, enablePagination]);

    // Show skeleton while loading
    if (!hasAnyActivities && isFetching) {
        return <RecentActivitySkeleton />;
    }

    // Only show empty state if not loading, has loaded once, and truly no activities
    if (!hasAnyActivities && !isFetching) {
        return (
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center space-x-2 text-base">
                        <Clock className="w-4 h-4" />
                        <span>Recent Activity</span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground text-center py-6 text-sm">
                        No recent activity. Create your first playlist to get started!
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="lg:h-full flex flex-col">
            <CardHeader className="flex-shrink-0 pb-3">
                <CardTitle className="flex items-center space-x-2 text-base">
                    <Clock className="w-4 h-4" />
                    <span>Recent Activity</span>
                </CardTitle>
            </CardHeader>
            <CardContent
                ref={scrollContainerRef}
                className="lg:flex-1 lg:overflow-y-auto lg:min-h-0 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-transparent hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/30"
            >
                <div className="space-y-4">
                    {displayedActivities.map((playlist, index) => {
                        const StatusIcon = getStatusIcon(playlist.status);

                        return (
                            <div
                                key={playlist.id}
                                className="flex gap-4 pb-4 border-b last:border-b-0 last:pb-0"
                            >
                                <div className="flex flex-col items-center pt-0.5">
                                    <div className={`p-2 rounded-full ${getStatusColor(playlist.status)}`}>
                                        <StatusIcon className={`w-4 h-4 ${playlist.status.toLowerCase() === 'generating' || playlist.status.toLowerCase() === 'pending' ? 'animate-spin' : ''}`} />
                                    </div>
                                    {index < activities.length - 1 && (
                                        <div className="w-px flex-1 bg-border mt-2" />
                                    )}
                                </div>

                                <div className="flex-1 space-y-2 min-w-0">
                                    <div className="flex items-start justify-between gap-2 sm:gap-3">
                                        <div className="flex-1 min-w-0 space-y-1.5">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                {playlist.name && (
                                                    <h4 className="font-semibold text-sm break-words">{cleanText(playlist.name)}</h4>
                                                )}
                                                <Badge
                                                    variant="outline"
                                                    className={`text-xs px-2 py-0.5 ${getStatusColor(playlist.status)} flex-shrink-0`}
                                                >
                                                    {playlist.status}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed break-words">
                                                {cleanText(playlist.mood_prompt)}
                                            </p>
                                        </div>
                                        {playlist.spotify_url && (
                                            <Link
                                                href={playlist.spotify_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="p-2 hover:bg-accent rounded-md transition-colors flex-shrink-0 self-start"
                                                aria-label="Open in Spotify"
                                            >
                                                <ExternalLink className="w-4 h-4" />
                                            </Link>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                                        <span className="flex items-center gap-1 flex-shrink-0">
                                            <Music className="w-3.5 h-3.5" />
                                            {playlist.track_count} tracks
                                        </span>
                                        {playlist.primary_emotion && (
                                            <>
                                                <span className="hidden sm:inline">·</span>
                                                <span className="capitalize break-words">
                                                    {playlist.primary_emotion}
                                                </span>
                                            </>
                                        )}
                                        <span className="sm:ml-auto flex-shrink-0">{formatTimeAgo(playlist.created_at)}</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {/* Loading indicator */}
                    {isLoading && (
                        <div className="flex items-center justify-center py-4">
                            <Loader className="w-4 h-4 animate-spin text-muted-foreground" />
                            <span className="ml-2 text-sm text-muted-foreground">Loading more...</span>
                        </div>
                    )}

                    {/* End of list indicator */}
                    {enablePagination && !hasMore && activities.length > 10 && (
                        <div className="text-center py-4 text-sm text-muted-foreground">
                            You&apos;ve reached the end of your activity history
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
