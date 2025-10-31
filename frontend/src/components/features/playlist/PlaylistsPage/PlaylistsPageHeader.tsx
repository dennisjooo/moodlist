"use client";

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { FeatureBadge } from '@/components/ui/feature-badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { PlaylistSortField, PlaylistSortOrder } from '@/lib/hooks/playlist';
import { cn } from '@/lib/utils';
import { ArrowDownWideNarrow, Check, Grid2x2, List, Music, Search, X } from 'lucide-react';
import { useMemo, useState } from 'react';

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
}: PlaylistsPageHeaderProps) {
    const [isSearchOpen, setIsSearchOpen] = useState(false);

    const activeSort = useMemo(() => {
        return (
            SORT_OPTIONS.find(option => option.sortBy === sortBy && option.sortOrder === sortOrder) ?? SORT_OPTIONS[0]
        );
    }, [sortBy, sortOrder]);
    const hasSearch = searchValue.trim().length > 0;

    return (
        <div className="mb-6 space-y-6">
            <div className="text-center">
                <FeatureBadge icon={Music} className="mb-3" ariaLabel="Feature badge">
                    Your Music History
                </FeatureBadge>

                <div className="space-y-2">
                    <h1 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                        My Playlists
                    </h1>
                    <p className="mx-auto max-w-2xl text-sm text-muted-foreground sm:text-base">
                        All your mood-based playlists in one place. Search, sort, and revisit every vibe you&apos;ve created.
                    </p>
                </div>
            </div>

            <div className="flex items-center justify-end gap-2">
                <Popover open={isSearchOpen} onOpenChange={setIsSearchOpen}>
                    <PopoverTrigger asChild>
                        <Button
                            variant="outline"
                            size="sm"
                            className={cn(
                                "gap-2",
                                hasSearch && "border-primary"
                            )}
                        >
                            <Search className="h-4 w-4" />
                            Search
                            {hasSearch && (
                                <Badge variant="secondary" className="ml-1 px-1.5 py-0 h-5 text-xs">
                                    1
                                </Badge>
                            )}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent align="center" className="w-80">
                        <div className="space-y-3">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    value={searchValue}
                                    onChange={event => onSearchChange(event.target.value)}
                                    placeholder="Search by mood prompt or playlist name"
                                    className="pl-9 pr-10 h-10"
                                    autoFocus
                                />
                                {hasSearch && (
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        onClick={onClearSearch}
                                        className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                                        aria-label="Clear search"
                                    >
                                        <X className="h-4 w-4" />
                                    </Button>
                                )}
                            </div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                Tip: try searching for moods like &ldquo;sunset run&rdquo;
                            </p>
                        </div>
                    </PopoverContent>
                </Popover>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm" className="gap-2">
                            <ArrowDownWideNarrow className="h-4 w-4" />
                            <span className="hidden sm:inline">{activeSort.label}</span>
                            <span className="sm:hidden">Sort</span>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-56">
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

                <div className="h-6 w-px bg-border" />

                <div className="flex items-center gap-1">
                    <Button
                        type="button"
                        variant={viewMode === 'grid' ? 'default' : 'ghost'}
                        size="sm"
                        aria-pressed={viewMode === 'grid'}
                        onClick={() => onViewModeChange('grid')}
                        className="gap-1.5 px-3"
                    >
                        <Grid2x2 className="h-4 w-4" />
                        <span className="hidden sm:inline">Grid</span>
                    </Button>
                    <Button
                        type="button"
                        variant={viewMode === 'list' ? 'default' : 'ghost'}
                        size="sm"
                        aria-pressed={viewMode === 'list'}
                        onClick={() => onViewModeChange('list')}
                        className="gap-1.5 px-3"
                    >
                        <List className="h-4 w-4" />
                        <span className="hidden sm:inline">List</span>
                    </Button>
                </div>
            </div>
        </div>
    );
}

