'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TooltipProvider } from '@/components/ui/tooltip';
import { usePlaylistEdits } from '@/lib/hooks';
import type { Track } from '@/lib/types/workflow';
import { Check, RotateCcw } from 'lucide-react';
import { TrackList } from './TrackList';
import { TrackSearch } from './TrackSearch';

export interface PlaylistEditorProps {
    sessionId: string;
    recommendations: Track[];
    isCompleted?: boolean;
    onSave?: () => void;
    onCancel?: () => void;
}

export function PlaylistEditor({
    sessionId,
    recommendations,
    isCompleted = false,
    onSave,
    onCancel
}: PlaylistEditorProps) {
    const {
        tracks,
        reorderTrack,
        removeTrack,
        addTrack,
        resetTracks,
        removingTracks,
        addingTracks,
        searchQuery,
        searchResults,
        isSearching,
        isSearchPending,
        searchTracks,
    } = usePlaylistEdits({ sessionId, initialTracks: recommendations });

    return (
        <TooltipProvider>
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                {/* Header */}
                <div className="space-y-3">
                    <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
                        Edit Your Playlist
                    </h1>
                    <p className="text-muted-foreground text-lg max-w-2xl">
                        {isCompleted ? 'Search and add tracks, or drag to reorder and remove songs.' : 'Drag tracks to reorder them, or remove songs you don\'t like.'}
                    </p>
                </div>

                {/* Two Column Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Left Column - Add Tracks */}
                    <TrackSearch
                        searchQuery={searchQuery}
                        searchResults={searchResults}
                        isSearching={isSearching}
                        isSearchPending={isSearchPending}
                        onSearchChange={searchTracks}
                        onAddTrack={addTrack}
                        addingTracks={addingTracks}
                        currentTracks={tracks}
                    />

                    {/* Right Column - Playlist */}
                    <div className="space-y-6">
                        <Card className="border-2 shadow-lg hover:shadow-xl transition-shadow duration-300">
                            <CardHeader className="pb-2">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle className="text-lg">Your Playlist</CardTitle>
                                        <p className="text-sm text-muted-foreground mt-1">{tracks.length} track{tracks.length !== 1 ? 's' : ''}</p>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={resetTracks}
                                        className="flex items-center gap-2 hover:scale-105 transition-all group"
                                    >
                                        <RotateCcw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
                                        Reset
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <TrackList
                                    tracks={tracks}
                                    onReorder={reorderTrack}
                                    onRemove={removeTrack}
                                    removingTracks={removingTracks}
                                />
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-4 pt-6 border-t">
                    <Button
                        variant="outline"
                        size="lg"
                        onClick={onCancel}
                        className="hover:scale-105 transition-transform"
                    >
                        {isCompleted ? 'Done Editing' : 'Cancel'}
                    </Button>
                    {!isCompleted && (
                        <Button
                            size="lg"
                            onClick={onSave}
                            disabled={tracks.length === 0}
                            className="flex items-center gap-2 shadow-lg hover:shadow-xl hover:scale-105 transition-all bg-gradient-to-r from-primary to-primary/90"
                        >
                            <Check className="w-4 h-4" />
                            Finalize Playlist ({tracks.length} tracks)
                        </Button>
                    )}
                </div>

                {/* Mobile Touch Instructions */}
                <div className="md:hidden animate-in slide-in-from-bottom-4 duration-500">
                    <div className="rounded-lg bg-gradient-to-r from-muted/50 to-muted/30 border border-dashed px-4 py-3 hover:border-solid transition-all">
                        <p className="text-sm text-muted-foreground">
                            <strong className="font-medium text-foreground">Tip:</strong> Touch and hold the grip handle (≡) to drag tracks on mobile devices.
                        </p>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    );
}

