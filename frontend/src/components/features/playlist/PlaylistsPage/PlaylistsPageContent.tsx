"use client";

import Navigation from '@/components/Navigation';
import { PlaylistGridSkeleton, PlaylistListSkeleton } from '@/components/shared/LoadingStates';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import { DotPattern } from '@/components/ui/dot-pattern';
import { usePlaylists, usePlaylistFormatting } from '@/lib/hooks/playlist';
import { useInfiniteScroll, useDebouncedSearch, useViewMode } from '@/lib/hooks';
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
        filters,
        setSearchQuery,
        setSort,
    } = usePlaylists();

    // Custom hooks for UI state management
    const [viewMode, setViewMode] = useViewMode('playlistViewMode', 'grid');
    const [searchValue, setSearchValue] = useDebouncedSearch(filters.search, setSearchQuery, 300);
    const { formatDate } = usePlaylistFormatting();

    const loadMoreRef = useInfiniteScroll(loadMore, {
        threshold: 500,
    });

    return (
        <div className="min-h-screen bg-background relative">
            {/* Fixed Dot Pattern Background */}
            <div className="fixed inset-0 z-0 opacity-0 animate-[fadeInDelayed_1.2s_ease-in-out_forwards]">
                <DotPattern
                    className={cn(
                        "[mask-image:radial-gradient(400px_circle_at_center,white,transparent)]",
                    )}
                />
            </div>

            {/* Navigation */}
            <Navigation />

            {/* Main Content */}
            <main className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                {!isUnauthorized && (playlists.length > 0 || isLoading || searchValue.trim().length > 0) && (
                    <PlaylistsPageHeader
                        searchValue={searchValue}
                        onSearchChange={setSearchValue}
                        onClearSearch={() => setSearchValue('')}
                        sortBy={filters.sortBy}
                        sortOrder={filters.sortOrder}
                        onSortChange={setSort}
                        viewMode={viewMode}
                        onViewModeChange={setViewMode}
                    />
                )}

                <CrossfadeTransition
                    isLoading={isLoading}
                    skeleton={viewMode === 'list' ? <PlaylistListSkeleton /> : <PlaylistGridSkeleton />}
                >
                    {isUnauthorized ? (
                        <UnauthorizedState />
                    ) : error ? (
                        <ErrorState error={error} onRetry={() => fetchPlaylists()} />
                    ) : playlists.length === 0 ? (
                        <div className="flex items-center justify-center min-h-[60vh]">
                            <EmptyState />
                        </div>
                    ) : (
                        <div className="space-y-12">
                            <PlaylistGrid
                                playlists={playlists}
                                onDelete={handleDelete}
                                formatDate={formatDate}
                                viewMode={viewMode}
                            />

                            <LoadMoreIndicator
                                hasMore={hasMore}
                                isLoadingMore={isLoadingMore}
                                playlistCount={playlists.length}
                                total={total}
                                loadMoreRef={loadMoreRef}
                            />
                        </div>
                    )}
                </CrossfadeTransition>
            </main>
        </div>
    );
}

