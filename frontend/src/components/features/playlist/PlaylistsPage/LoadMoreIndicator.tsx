import { Loader2 } from 'lucide-react';

interface LoadMoreIndicatorProps {
    hasMore: boolean;
    isLoadingMore: boolean;
    playlistCount: number;
    total: number;
    loadMoreRef: (node: HTMLDivElement | null) => void;
}

export function LoadMoreIndicator({
    hasMore,
    isLoadingMore,
    playlistCount,
    total,
    loadMoreRef
}: LoadMoreIndicatorProps) {
    if (!hasMore && playlistCount > 0) {
        return (
            <div className="py-8 text-center text-muted-foreground">
                <p>You've reached the end of your playlists</p>
                <p className="text-sm mt-2">
                    Showing {playlistCount} of {total} playlists
                </p>
            </div>
        );
    }

    if (hasMore) {
        return (
            <div
                ref={loadMoreRef}
                className="py-8 flex justify-center min-h-[100px] items-center"
            >
                {isLoadingMore && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Loading more playlists...</span>
                    </div>
                )}
            </div>
        );
    }

    return null;
}

