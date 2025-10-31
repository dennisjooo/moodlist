"use client";

import Navigation from '@/components/Navigation';
import { PlaylistGridSkeleton } from '@/components/shared/LoadingStates';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import { DotPattern } from '@/components/ui/dot-pattern';
import { usePlaylists } from '@/lib/hooks/playlist';
import { useInfiniteScroll } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
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

    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [searchValue, setSearchValue] = useState(filters.search);

    const loadMoreRef = useInfiniteScroll(loadMore, {
        threshold: 500,
    });

    useEffect(() => {
        setSearchValue(filters.search);
    }, [filters.search]);

    useEffect(() => {
        const timeout = window.setTimeout(() => {
            setSearchQuery(searchValue);
        }, 300);

        return () => {
            window.clearTimeout(timeout);
        };
    }, [searchValue, setSearchQuery]);

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

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
                {!isUnauthorized && (
                    <PlaylistsPageHeader
                        searchValue={searchValue}
                        onSearchChange={setSearchValue}
                        onClearSearch={() => setSearchValue('')}
                        sortBy={filters.sortBy}
                        sortOrder={filters.sortOrder}
                        onSortChange={setSort}
                        viewMode={viewMode}
                        onViewModeChange={setViewMode}
                        total={total}
                        visibleCount={playlists.length}
                    />
                )}

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
                                    viewMode={viewMode}
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
            </main>
        </div>
    );
}

