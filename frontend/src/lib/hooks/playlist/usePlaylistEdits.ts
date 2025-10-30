'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { arrayMove } from '@dnd-kit/sortable';
import { useToast } from '../ui/useToast';
import { logger } from '@/lib/utils/logger';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import type { Track, SearchTrack } from '@/lib/types/workflow';

interface UsePlaylistEditsOptions {
    sessionId: string;
    initialTracks: Track[];
}

/**
 * Custom hook to manage playlist edit operations
 * Handles track reordering, removal, addition, and search with optimistic updates
 */
export function usePlaylistEdits({ sessionId, initialTracks }: UsePlaylistEditsOptions) {
    const { error: showError } = useToast();
    const { applyCompletedEdit, searchTracks: searchTracksApi } = useWorkflow();

    // Deduplicate recommendations by track_id to prevent React key conflicts
    const deduplicatedTracks = useMemo(() =>
        initialTracks.filter((track, index, arr) =>
            arr.findIndex(t => t.track_id === track.track_id) === index
        ), [initialTracks]
    );

    const [tracks, setTracks] = useState<Track[]>(deduplicatedTracks);
    const [removingTracks, setRemovingTracks] = useState<Set<string>>(new Set());
    const [addingTracks, setAddingTracks] = useState<Set<string>>(new Set());

    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<SearchTrack[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isSearchPending, setIsSearchPending] = useState(false);

    const latestSearchQueryRef = useRef<string>('');
    const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Sync tracks when recommendations prop changes (from context updates)
    useEffect(() => {
        setTracks(deduplicatedTracks);
    }, [deduplicatedTracks]);

    // Cleanup search timeout on unmount
    useEffect(() => {
        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, []);

    const reorderTrack = useCallback(async (oldIndex: number, newIndex: number) => {
        if (oldIndex === -1 || newIndex === -1) return;

        const trackId = tracks[oldIndex].track_id;

        // Optimistically update UI
        const newTracks = arrayMove(tracks, oldIndex, newIndex);
        setTracks(newTracks);

        try {
            await applyCompletedEdit('reorder', {
                trackId,
                newPosition: newIndex,
            });
        } catch (error) {
            // Revert on error
            setTracks(tracks);
            const errorMessage = error instanceof Error ? error.message : 'Failed to reorder track';
            showError(errorMessage);
            logger.error('Failed to reorder track', error, { component: 'usePlaylistEdits', sessionId });
        }
    }, [tracks, applyCompletedEdit, sessionId, showError]);

    const removeTrack = useCallback(async (trackId: string) => {
        setRemovingTracks(prev => new Set(prev).add(trackId));

        try {
            // Optimistically update UI
            setTracks(prev => prev.filter(track => track.track_id !== trackId));

            await applyCompletedEdit('remove', { trackId });
        } catch (error) {
            // Revert on error
            setTracks(deduplicatedTracks);
            const errorMessage = error instanceof Error ? error.message : 'Failed to remove track';
            showError(errorMessage);
            logger.error('Failed to remove track', error, { component: 'usePlaylistEdits', trackId });
        } finally {
            setRemovingTracks(prev => {
                const newSet = new Set(prev);
                newSet.delete(trackId);
                return newSet;
            });
        }
    }, [applyCompletedEdit, deduplicatedTracks, showError]);

    const addTrack = useCallback(async (trackUri: string, trackInfo?: SearchTrack) => {
        setAddingTracks(prev => new Set(prev).add(trackUri));

        try {
            // Apply edit to server first
            await applyCompletedEdit('add', { trackUri });

            // On success, immediately add track to UI
            if (trackInfo) {
                const optimisticTrack: Track = {
                    track_id: trackInfo.track_id,
                    track_name: trackInfo.track_name,
                    artists: trackInfo.artists,
                    spotify_uri: trackInfo.spotify_uri,
                    confidence_score: 0.5, // Default for user-added tracks
                    reasoning: 'Added by user',
                    source: 'user_added'
                };

                setTracks(prev => [...prev, optimisticTrack]);
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to add track';
            showError(errorMessage);
            logger.error('Failed to add track', error, { component: 'usePlaylistEdits', trackUri });
        } finally {
            setAddingTracks(prev => {
                const newSet = new Set(prev);
                newSet.delete(trackUri);
                return newSet;
            });
        }
    }, [applyCompletedEdit, showError]);

    const searchTracks = useCallback((query: string) => {
        setSearchQuery(query);

        // Clear any existing timeout
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        // Store the latest query in ref to prevent race conditions
        latestSearchQueryRef.current = query;

        if (!query.trim()) {
            setSearchResults([]);
            setIsSearching(false);
            setIsSearchPending(false);
            return;
        }

        // Set pending state immediately when user types
        setIsSearchPending(true);

        // Debounce search - wait 300ms after user stops typing
        searchTimeoutRef.current = setTimeout(async () => {
            const currentSearchQuery = query;
            setIsSearching(true);
            setIsSearchPending(false);

            try {
                const results = await searchTracksApi(query);

                // Only update results if this is still the latest search
                if (latestSearchQueryRef.current === currentSearchQuery) {
                    setSearchResults(results.tracks || []);
                }
            } catch (error) {
                logger.error('Search failed', error, { component: 'usePlaylistEdits' });
                // Only show error if this is still the latest search
                if (latestSearchQueryRef.current === currentSearchQuery) {
                    showError('Failed to search tracks');
                }
            } finally {
                // Only update loading state if this is still the latest search
                if (latestSearchQueryRef.current === currentSearchQuery) {
                    setIsSearching(false);
                }
            }
        }, 300);
    }, [searchTracksApi, showError]);

    const resetTracks = useCallback(() => {
        setTracks(deduplicatedTracks);
    }, [deduplicatedTracks]);

    return {
        // Track state
        tracks,

        // Edit operations
        reorderTrack,
        removeTrack,
        addTrack,
        resetTracks,

        // Edit state
        removingTracks,
        addingTracks,

        // Search state
        searchQuery,
        searchResults,
        isSearching,
        isSearchPending,
        searchTracks,
    };
}

