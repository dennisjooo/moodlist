import type { PlaylistSortField, PlaylistSortOrder } from '@/lib/hooks/playlist';

export interface SortOption {
    id: string;
    label: string;
    sortBy: PlaylistSortField;
    sortOrder: PlaylistSortOrder;
}

export const SORT_OPTIONS: SortOption[] = [
    {
        id: 'recent',
        label: 'Newest first',
        sortBy: 'created_at',
        sortOrder: 'desc',
    },
    {
        id: 'oldest',
        label: 'Oldest first',
        sortBy: 'created_at',
        sortOrder: 'asc',
    },
    {
        id: 'name-asc',
        label: 'Name A to Z',
        sortBy: 'name',
        sortOrder: 'asc',
    },
    {
        id: 'name-desc',
        label: 'Name Z to A',
        sortBy: 'name',
        sortOrder: 'desc',
    },
    {
        id: 'tracks-desc',
        label: 'Most tracks',
        sortBy: 'track_count',
        sortOrder: 'desc',
    },
    {
        id: 'tracks-asc',
        label: 'Fewest tracks',
        sortBy: 'track_count',
        sortOrder: 'asc',
    },
];

