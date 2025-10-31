import { playlistAPI, UserPlaylist } from '@/lib/api/playlist';
import { logger } from '@/lib/utils/logger';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActiveWorkflow } from '../workflow/useActiveWorkflows';

export type PlaylistSortField = 'created_at' | 'name' | 'track_count';
export type PlaylistSortOrder = 'asc' | 'desc';

export interface PlaylistFilters {
    search: string;
    sortBy: PlaylistSortField;
    sortOrder: PlaylistSortOrder;
}

interface UsePlaylistsReturn {
    playlists: UserPlaylist[];
    isLoading: boolean;
    isLoadingMore: boolean;
    error: string | null;
    isUnauthorized: boolean;
    hasMore: boolean;
    total: number;
    fetchPlaylists: (isLoadMore?: boolean) => Promise<void>;
    loadMore: () => void;
    handleDelete: (playlistId: number) => Promise<void>;
    filters: PlaylistFilters;
    setSearchQuery: (search: string) => void;
    setSort: (sortBy: PlaylistSortField, sortOrder: PlaylistSortOrder) => void;
}

export function usePlaylists(): UsePlaylistsReturn {
    const [playlists, setPlaylists] = useState<UserPlaylist[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isUnauthorized, setIsUnauthorized] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [total, setTotal] = useState(0);
    const offsetRef = useRef(0);
    const [filters, setFilters] = useState<PlaylistFilters>({
        search: '',
        sortBy: 'created_at',
        sortOrder: 'desc',
    });

    const fetchPlaylists = useCallback(async (isLoadMore = false) => {
        try {
            if (isLoadMore) {
                setIsLoadingMore(true);
            } else {
                setIsLoading(true);
                offsetRef.current = 0;
            }

            setIsUnauthorized(false);

            const searchParam = filters.search.trim();

            const response = await playlistAPI.getUserPlaylists(
                12,
                offsetRef.current,
                ['failed', 'cancelled'],
                searchParam ? searchParam : undefined,
                filters.sortBy,
                filters.sortOrder,
            );

            if (isLoadMore) {
                setPlaylists(prev => [...prev, ...response.playlists]);
            } else {
                setPlaylists(response.playlists);
            }

            setTotal(response.total);
            offsetRef.current += response.playlists.length;
            setHasMore(offsetRef.current < response.total);

        } catch (err) {
            logger.error('Failed to fetch playlists', err, { component: 'usePlaylists' });
            const errorMessage = err instanceof Error ? err.message : 'Failed to load playlists';

            if (errorMessage.includes('401')) {
                setIsUnauthorized(true);
            } else {
                setError(errorMessage);
            }
        } finally {
            setIsLoading(false);
            setIsLoadingMore(false);
        }
    }, [filters.search, filters.sortBy, filters.sortOrder]);

    const loadMore = useCallback(() => {
        if (!isLoadingMore && hasMore && !isLoading) {
            fetchPlaylists(true);
        }
    }, [isLoadingMore, hasMore, isLoading, fetchPlaylists]);

    const handleDelete = useCallback(async (playlistId: number) => {
        try {
            await playlistAPI.deletePlaylist(playlistId);
            setPlaylists(prev => prev.filter(p => p.id !== playlistId));
        } catch (err) {
            logger.error('Failed to delete playlist', err, { component: 'usePlaylists' });
            setError('Failed to delete playlist. Please try again.');
            setTimeout(() => setError(null), 5000);
        }
    }, []);

    // Listen for workflow completion events to auto-refresh playlists
    const handleWorkflowUpdate = useCallback((event: CustomEvent<ActiveWorkflow>) => {
        const { status } = event.detail;

        if (status === 'completed') {
            logger.info('Workflow completed, refreshing playlists', {
                component: 'usePlaylists',
                sessionId: event.detail.sessionId
            });

            setTimeout(() => {
                fetchPlaylists(false);
            }, 1000);
        }
    }, [fetchPlaylists]);

    useEffect(() => {
        fetchPlaylists();
    }, [fetchPlaylists]);

    useEffect(() => {
        window.addEventListener('workflow-updated', handleWorkflowUpdate as EventListener);

        return () => {
            window.removeEventListener('workflow-updated', handleWorkflowUpdate as EventListener);
        };
    }, [handleWorkflowUpdate]);

    const setSearchQuery = useCallback((search: string) => {
        setFilters(prev => {
            if (prev.search === search) {
                return prev;
            }
            return {
                ...prev,
                search,
            };
        });
    }, []);

    const setSort = useCallback((sortBy: PlaylistSortField, sortOrder: PlaylistSortOrder) => {
        setFilters(prev => {
            if (prev.sortBy === sortBy && prev.sortOrder === sortOrder) {
                return prev;
            }
            return {
                ...prev,
                sortBy,
                sortOrder,
            };
        });
    }, []);

    return {
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
    };
}

