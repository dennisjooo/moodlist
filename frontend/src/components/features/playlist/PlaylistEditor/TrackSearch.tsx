'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import type { Track } from '@/lib/types/track';
import type { SearchTrack } from '@/lib/types/workflow';
import { cn } from '@/lib/utils';
import { Check, ChevronDown, ChevronUp, Loader2, Plus, Search } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';
import TrackDetailsTooltip from '../TrackDetailsTooltip';

export interface TrackSearchProps {
    searchQuery: string;
    searchResults: SearchTrack[];
    isSearching: boolean;
    isSearchPending: boolean;
    onSearchChange: (query: string) => void;
    onAddTrack: (trackUri: string, trackInfo: SearchTrack) => void;
    addingTracks: Set<string>;
    currentTracks: Track[];
}

export function TrackSearch({
    searchQuery,
    searchResults,
    isSearching,
    isSearchPending,
    onSearchChange,
    onAddTrack,
    addingTracks,
    currentTracks
}: TrackSearchProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <Card className="lg:sticky lg:top-20 h-fit">
            <CardHeader>
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                        <CardTitle className="text-lg">Add Tracks</CardTitle>
                        <p className="text-sm text-muted-foreground mt-1">
                            Search Spotify to find and add songs to your playlist
                        </p>
                    </div>
                    <button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="lg:hidden p-2 hover:bg-accent rounded-md transition-colors flex-shrink-0 self-center"
                        aria-label={isCollapsed ? "Expand add tracks" : "Collapse add tracks"}
                    >
                        {isCollapsed ? (
                            <ChevronDown className="w-5 h-5" />
                        ) : (
                            <ChevronUp className="w-5 h-5" />
                        )}
                    </button>
                </div>
            </CardHeader>
            <div
                className={cn(
                    "grid transition-all duration-300 ease-in-out",
                    isCollapsed ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
                )}
            >
                <div className="overflow-hidden">
                    <CardContent className="space-y-4">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <Input
                                placeholder="Search for tracks to add..."
                                value={searchQuery}
                                onChange={(e) => onSearchChange(e.target.value)}
                                className="pl-10"
                            />
                        </div>

                        {searchResults.length > 0 && (
                            <div className="relative">
                                <div className={cn(
                                    "space-y-2 max-h-[600px] overflow-y-auto pr-2 transition-all duration-200",
                                    isSearching && "blur-sm opacity-50 pointer-events-none"
                                )}>
                                    {searchResults.map((track) => {
                                        const isAlreadyAdded = currentTracks.some(t => t.track_id === track.track_id);
                                        const isAdding = addingTracks.has(track.spotify_uri);

                                        return (
                                            <div
                                                key={track.track_id}
                                                className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                                            >
                                                {track.album_image && (
                                                    <Image
                                                        src={track.album_image}
                                                        alt={track.album || 'Album cover'}
                                                        width={48}
                                                        height={48}
                                                        className="w-12 h-12 rounded"
                                                    />
                                                )}
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
                                                    <p className="text-xs text-muted-foreground truncate">
                                                        {track.artists.join(', ')}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2 flex-shrink-0">
                                                    <TrackDetailsTooltip spotifyUri={track.spotify_uri} />
                                                    {isAlreadyAdded ? (
                                                        <div className="flex items-center gap-1 text-green-600">
                                                            <Check className="w-4 h-4" />
                                                        </div>
                                                    ) : (
                                                        <Button
                                                            size="sm"
                                                            onClick={() => onAddTrack(track.spotify_uri, track)}
                                                            className={cn(
                                                                "flex items-center gap-1",
                                                                isAdding ? "bg-green-600 hover:bg-green-700 text-white" : ""
                                                            )}
                                                        >
                                                            {isAdding ? (
                                                                <>
                                                                    <Loader2 className="w-3 h-3 animate-spin" />
                                                                    Adding
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Plus className="w-3 h-3" />
                                                                    Add
                                                                </>
                                                            )}
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {isSearching && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm rounded-lg">
                                        <div className="flex flex-col items-center gap-2">
                                            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                            <p className="text-sm text-muted-foreground">Searching...</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {!searchQuery ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <Search className="w-12 h-12 mx-auto mb-3 opacity-20" />
                                <p className="text-sm">Start typing to search for tracks</p>
                            </div>
                        ) : (isSearching || isSearchPending) ? (
                            searchResults.length === 0 ? (
                                <div className="flex items-center justify-center py-8">
                                    <div className="flex flex-col items-center gap-2">
                                        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                        <p className="text-sm text-muted-foreground">Searching...</p>
                                    </div>
                                </div>
                            ) : null
                        ) : searchResults.length === 0 && searchQuery.length >= 2 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <p className="text-sm">No results found for &quot;{searchQuery}&quot;</p>
                            </div>
                        ) : null}
                    </CardContent>
                </div>
            </div>
        </Card>
    );
}

