import Navigation from '@/components/Navigation';
import { PlaylistGridSkeleton } from '@/components/shared/LoadingStates';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import { DotPattern } from '@/components/ui/dot-pattern';
import { usePlaylists } from '@/lib/hooks/playlist';
import { useInfiniteScroll } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { LoadMoreIndicator } from './LoadMoreIndicator';
import { PlaylistGrid } from './PlaylistGrid';
import { PlaylistsPageHeader } from './PlaylistsPageHeader';
import { UnauthorizedState } from './UnauthorizedState';

export function PlaylistsPageContent() {
    const {
        playlists,
        isLoading,
        isLoadingMore,
        error,
        isUnauthorized,
        hasMore,
        total,
        fetchPlaylists,
        loadMore,
        handleDelete,
    } = usePlaylists();

    const loadMoreRef = useInfiniteScroll(loadMore, {
        threshold: 500,
    });

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    return (
        <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-background via-background/95 to-background">
            <div
                aria-hidden="true"
                className="pointer-events-none absolute left-[-18%] top-[-18%] h-[32rem] w-[32rem] -z-20 rounded-full bg-primary/25 blur-[130px] opacity-70"
            />
            <div
                aria-hidden="true"
                className="pointer-events-none absolute right-[-20%] bottom-[-25%] h-[30rem] w-[30rem] -z-20 rounded-full bg-muted/40 blur-[150px] opacity-70"
            />

            <div className="pointer-events-none fixed inset-0 -z-10 opacity-0 mix-blend-screen animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                        "text-muted-foreground/10",
                    )}
                />
            </div>

            {/* Navigation */}
            <div className="relative z-20">
                <Navigation />
            </div>

            {/* Main Content */}
            <main className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-20 pt-28 sm:px-6 lg:px-8">
                <section className="rounded-3xl border border-border/40 bg-background/80 p-6 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl sm:p-8">
                    {!isUnauthorized && <PlaylistsPageHeader />}

                    <CrossfadeTransition
                        isLoading={isLoading}
                        skeleton={<PlaylistGridSkeleton />}
                    >
                        <div className="space-y-12">
                            {isUnauthorized ? (
                                <UnauthorizedState />
                            ) : error ? (
                                <ErrorState error={error} onRetry={() => fetchPlaylists()} />
                            ) : playlists.length === 0 ? (
                                <EmptyState />
                            ) : (
                                <>
                                    <PlaylistGrid
                                        playlists={playlists}
                                        onDelete={handleDelete}
                                        formatDate={formatDate}
                                    />

                                    <LoadMoreIndicator
                                        hasMore={hasMore}
                                        isLoadingMore={isLoadingMore}
                                        playlistCount={playlists.length}
                                        total={total}
                                        loadMoreRef={loadMoreRef}
                                    />
                                </>
                            )}
                        </div>
                    </CrossfadeTransition>
                </section>
            </main>
        </div>
    );
}

