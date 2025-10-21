'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Track } from '@/lib/contexts/WorkflowContext';
import { usePlaylistEdits } from '@/lib/hooks/usePlaylistEdits';
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
        <div className="space-y-6">
            {/* Header */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        ✏️ Edit Your Playlist
                    </CardTitle>
                    <p className="text-muted-foreground">
                        {isCompleted ? 'Search and add tracks, or drag to reorder and remove songs.' : 'Drag tracks to reorder them, or remove songs you don\'t like.'}
                    </p>
                </CardHeader>
            </Card>

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center justify-between">
                                <span>Playlist Tracks ({tracks.length})</span>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={resetTracks}
                                    className="flex items-center gap-2"
                                >
                                    <RotateCcw className="w-4 h-4" />
                                    Reset
                                </Button>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
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
            <div className="flex gap-3">
                <Button
                    variant="outline"
                    onClick={onCancel}
                    className="flex-1"
                >
                    {isCompleted ? 'Done Editing' : 'Cancel'}
                </Button>
                {!isCompleted && (
                    <Button
                        onClick={onSave}
                        disabled={tracks.length === 0}
                        className="flex-1 flex items-center gap-2"
                    >
                        <Check className="w-4 h-4" />
                        Finalize Playlist ({tracks.length} tracks)
                    </Button>
                )}
            </div>

            {/* Mobile Touch Instructions */}
            <div className="md:hidden">
                <Card className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="pt-4">
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            💡 <strong>Tip:</strong> Touch and hold the grip handle (≡) to drag tracks on mobile devices.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

