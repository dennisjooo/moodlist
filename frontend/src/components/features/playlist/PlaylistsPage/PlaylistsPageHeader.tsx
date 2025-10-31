"use client";

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PlaylistSortField, PlaylistSortOrder } from '@/lib/hooks/playlist';
import { cn } from '@/lib/utils';
import { ArrowDownWideNarrow, Check, Grid2x2, List, Music, Search, X } from 'lucide-react';
import { useMemo } from 'react';

interface SortOption {
    id: string;
    label: string;
    sortBy: PlaylistSortField;
    sortOrder: PlaylistSortOrder;
}

const SORT_OPTIONS: SortOption[] = [
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

interface PlaylistsPageHeaderProps {
    searchValue: string;
    onSearchChange: (value: string) => void;
    onClearSearch: () => void;
    sortBy: PlaylistSortField;
    sortOrder: PlaylistSortOrder;
    onSortChange: (sortBy: PlaylistSortField, sortOrder: PlaylistSortOrder) => void;
    viewMode: 'grid' | 'list';
    onViewModeChange: (view: 'grid' | 'list') => void;
    total: number;
    visibleCount: number;
}

export function PlaylistsPageHeader({
    searchValue,
    onSearchChange,
    onClearSearch,
    sortBy,
    sortOrder,
    onSortChange,
    viewMode,
    onViewModeChange,
    total,
    visibleCount,
}: PlaylistsPageHeaderProps) {
    const activeSort = useMemo(() => {
        return (
            SORT_OPTIONS.find(option => option.sortBy === sortBy && option.sortOrder === sortOrder) ?? SORT_OPTIONS[0]
        );
    }, [sortBy, sortOrder]);

    const formattedTotal = useMemo(() => total.toLocaleString(), [total]);
    const formattedVisible = useMemo(() => visibleCount.toLocaleString(), [visibleCount]);
    const hasSearch = searchValue.trim().length > 0;

    return (
        <div className="mb-12 space-y-8">
            <div className="text-center space-y-4">
                <Badge variant="outline" className="px-4 py-1 flex items-center gap-2 w-fit mx-auto">
                    <Music className="w-4 h-4" />
                    Your Music History
                </Badge>

                <div className="space-y-3">
                    <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
                        My Playlists
                    </h1>
                    <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                        All your mood-based playlists in one place. Search, sort, and revisit every vibe you&apos;ve created.
                    </p>
                    <p className="text-sm text-muted-foreground">
                        Showing {formattedVisible} of {formattedTotal} playlists
                        {hasSearch ? ' (filtered)' : ''}.
                    </p>
                </div>
            </div>

            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="w-full lg:max-w-xl">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            value={searchValue}
                            onChange={event => onSearchChange(event.target.value)}
                            placeholder="Search by mood prompt or playlist name"
                            className="pl-9 pr-10"
                        />
                        {hasSearch && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={onClearSearch}
                                className="absolute right-1 top-1/2 -translate-y-1/2 text-muted-foreground"
                                aria-label="Clear search"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                        Tip: try searching for moods like &ldquo;sunset run&rdquo; or &ldquo;focus&rdquo;.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm" className="min-w-[170px] justify-start">
                                <ArrowDownWideNarrow className="h-4 w-4" />
                                <span className="truncate">Sort: {activeSort.label}</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel>Sort playlists</DropdownMenuLabel>
                            {SORT_OPTIONS.map(option => (
                                <DropdownMenuItem
                                    key={option.id}
                                    onSelect={event => {
                                        event.preventDefault();
                                        onSortChange(option.sortBy, option.sortOrder);
                                    }}
                                >
                                    {option.label}
                                    {option.sortBy === sortBy && option.sortOrder === sortOrder && (
                                        <Check className="ml-auto h-4 w-4" />
                                    )}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>

                    <div className="flex items-center gap-1 rounded-md border border-border/70 bg-background/80 p-1">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            aria-pressed={viewMode === 'grid'}
                            onClick={() => onViewModeChange('grid')}
                            className={cn(
                                'gap-1.5 px-3',
                                viewMode === 'grid' && 'bg-primary text-primary-foreground hover:bg-primary/90 border-primary',
                            )}
                        >
                            <Grid2x2 className="h-4 w-4" />
                            <span className="hidden sm:inline">Grid</span>
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            aria-pressed={viewMode === 'list'}
                            onClick={() => onViewModeChange('list')}
                            className={cn(
                                'gap-1.5 px-3',
                                viewMode === 'list' && 'bg-primary text-primary-foreground hover:bg-primary/90 border-primary',
                            )}
                        >
                            <List className="h-4 w-4" />
                            <span className="hidden sm:inline">List</span>
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

