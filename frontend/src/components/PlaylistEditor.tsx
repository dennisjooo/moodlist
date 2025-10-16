'use client';

import {
  closestCenter,
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useWorkflow } from '@/lib/workflowContext';
import {
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  GripVertical,
  Loader2,
  Music,
  Plus,
  RotateCcw,
  Search,
  Star,
  Trash2
} from 'lucide-react';

interface Track {
  track_id: string;
  track_name: string;
  artists: string[];
  spotify_uri?: string;
  confidence_score: number;
  reasoning: string;
  source: string;
}

interface PlaylistEditorProps {
  sessionId: string;
  recommendations: Track[];
  isCompleted?: boolean;
  onSave?: () => void;
  onCancel?: () => void;
}

interface SortableTrackItemProps {
  track: Track;
  index: number;
  onRemove: (trackId: string) => void;
  isRemoving: boolean;
}

function SortableTrackItem({ track, index, onRemove, isRemoving }: SortableTrackItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: track.track_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-center gap-4 p-4 rounded-lg border bg-card transition-all duration-200",
        isDragging && "shadow-lg scale-105 z-50 bg-accent",
        !isDragging && "hover:bg-accent/50"
      )}
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        className="flex-shrink-0 cursor-grab active:cursor-grabbing touch-none"
        style={{ touchAction: 'none' }}
      >
        <GripVertical className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
      </div>

      {/* Track Number */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
        {index + 1}
      </div>

      {/* Track Info */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium truncate">{track.track_name}</h4>
        <p className="text-sm text-muted-foreground truncate">
          {track.artists.join(', ')}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
            <span className="text-xs text-muted-foreground">
              {Math.round(track.confidence_score * 30 + 70)}%
            </span>
          </div>
          <Badge variant="outline" className="text-xs capitalize">
            {track.source}
          </Badge>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {track.spotify_uri && (
          <Button size="sm" variant="ghost" asChild>
            <a
              href={(() => {
                const uri = track.spotify_uri;
                if (uri.startsWith('http')) return uri;
                if (uri.startsWith('spotify:track:')) {
                  return `https://open.spotify.com/track/${uri.split(':')[2]}`;
                }
                return `https://open.spotify.com/track/${uri}`;
              })()}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </Button>
        )}

        <Button
          size="sm"
          variant="ghost"
          onClick={() => onRemove(track.track_id)}
          disabled={isRemoving}
          className="p-2 text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          {isRemoving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  );
}

export default function PlaylistEditor({
  sessionId,
  recommendations,
  isCompleted = false,
  onSave,
  onCancel
}: PlaylistEditorProps) {
  const { applyCompletedEdit, saveToSpotify, searchTracks } = useWorkflow();
  const [tracks, setTracks] = useState<Track[]>(recommendations);
  const [removingTracks, setRemovingTracks] = useState<Set<string>>(new Set());
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [editReasoning, setEditReasoning] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchPending, setIsSearchPending] = useState(false);
  const [addingTracks, setAddingTracks] = useState<Set<string>>(new Set());
  const [isAddTracksCollapsed, setIsAddTracksCollapsed] = useState(false);

  // Track the latest search query to prevent race conditions
  const latestSearchQueryRef = useRef<string>('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Sync tracks when recommendations prop changes (from context updates)
  useEffect(() => {
    setTracks(recommendations);
  }, [recommendations]);

  // Cleanup search timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  // Set up sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px of movement before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = tracks.findIndex((track) => track.track_id === active.id);
      const newIndex = tracks.findIndex((track) => track.track_id === over.id);

      if (oldIndex !== -1 && newIndex !== -1) {
        // Optimistically update UI
        const newTracks = arrayMove(tracks, oldIndex, newIndex);
        setTracks(newTracks);

        try {
          // Always use applyCompletedEdit - it handles both draft and saved playlists
          await applyCompletedEdit('reorder', {
            trackId: active.id as string,
            newPosition: newIndex,
          });
        } catch (error) {
          // Revert on error
          setTracks(tracks);
          const errorMessage = error instanceof Error ? error.message : 'Failed to reorder track';
          setError(errorMessage);
          console.error('Failed to reorder track:', error);
        }
      }
    }
  }, [tracks, applyCompletedEdit]);

  const handleRemoveTrack = useCallback(async (trackId: string) => {
    setRemovingTracks(prev => new Set(prev).add(trackId));

    try {
      // Optimistically update UI
      setTracks(prev => prev.filter(track => track.track_id !== trackId));

      // Always use applyCompletedEdit - it handles both draft and saved playlists
      await applyCompletedEdit('remove', { trackId });
    } catch (error) {
      // Revert on error
      setTracks(recommendations);
      const errorMessage = error instanceof Error ? error.message : 'Failed to remove track';
      setError(errorMessage);
      console.error('Failed to remove track:', error);
    } finally {
      setRemovingTracks(prev => {
        const newSet = new Set(prev);
        newSet.delete(trackId);
        return newSet;
      });
    }
  }, [applyCompletedEdit, recommendations]);

  const handleFinalize = useCallback(() => {
    // Just close the editor, don't auto-save to Spotify
    onSave?.();
  }, [onSave]);

  const handleReset = useCallback(() => {
    setTracks(recommendations);
    setEditReasoning('');
  }, [recommendations]);

  const handleSearch = useCallback((query: string) => {
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
        const results = await searchTracks(query);

        // Only update results if this is still the latest search
        if (latestSearchQueryRef.current === currentSearchQuery) {
          setSearchResults(results.tracks || []);
        }
      } catch (error) {
        console.error('Search failed:', error);
        // Only show error if this is still the latest search
        if (latestSearchQueryRef.current === currentSearchQuery) {
          setError('Failed to search tracks');
        }
      } finally {
        // Only update loading state if this is still the latest search
        if (latestSearchQueryRef.current === currentSearchQuery) {
          setIsSearching(false);
        }
      }
    }, 300);
  }, [searchTracks]);

  const handleAddTrack = useCallback(async (trackUri: string) => {
    setAddingTracks(prev => new Set(prev).add(trackUri));

    // Find the track in search results to add optimistically
    const trackToAdd = searchResults.find(track => track.spotify_uri === trackUri);

    try {
      // Apply edit to server first (keep spinner during this)
      await applyCompletedEdit('add', { trackUri });

      // On success (200), immediately add track to UI and show checkmark
      if (trackToAdd) {
        const optimisticTrack: Track = {
          track_id: trackToAdd.track_id,
          track_name: trackToAdd.track_name,
          artists: trackToAdd.artists,
          spotify_uri: trackToAdd.spotify_uri,
          confidence_score: 0.5, // Default for user-added tracks
          reasoning: 'Added by user',
          source: 'user_added'
        };

        setTracks(prev => [...prev, optimisticTrack]);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to add track';
      setError(errorMessage);
      console.error('Failed to add track:', error);
    } finally {
      setAddingTracks(prev => {
        const newSet = new Set(prev);
        newSet.delete(trackUri);
        return newSet;
      });
    }
  }, [applyCompletedEdit, searchResults]);

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

      {/* Error Display */}
      {error && (
        <Alert className="border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800">
          <AlertDescription className="text-red-800 dark:text-red-200">
            {error}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="ml-2 h-auto p-1 text-red-600 hover:text-red-800"
            >
              ✕
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Add Tracks or Info */}
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
                onClick={() => setIsAddTracksCollapsed(!isAddTracksCollapsed)}
                className="lg:hidden p-2 hover:bg-accent rounded-md transition-colors flex-shrink-0 self-center"
                aria-label={isAddTracksCollapsed ? "Expand add tracks" : "Collapse add tracks"}
              >
                {isAddTracksCollapsed ? (
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
              isAddTracksCollapsed ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
            )}
          >
            <div className="overflow-hidden">
              <CardContent className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search for tracks to add..."
                    value={searchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {searchResults.length > 0 && (
                  <div className="relative">
                    <div className={cn(
                      "space-y-2 max-h-[600px] overflow-y-auto pr-2 transition-all duration-200",
                      isSearching && "blur-sm opacity-50 pointer-events-none"
                    )}>
                      {searchResults.map((track) => (
                        <div
                          key={track.track_id}
                          className="flex items-center gap-3 p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                        >
                          {track.album_image && (
                            <img
                              src={track.album_image}
                              alt={track.album}
                              className="w-12 h-12 rounded"
                            />
                          )}
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm truncate">{track.track_name}</h4>
                            <p className="text-xs text-muted-foreground truncate">
                              {track.artists.join(', ')}
                            </p>
                          </div>
                          {(() => {
                            const isAlreadyAdded = tracks.some(t => t.track_id === track.track_id);
                            const isAdding = addingTracks.has(track.spotify_uri);

                            if (isAlreadyAdded) {
                              return (
                                <div className="flex items-center gap-1 flex-shrink-0 text-green-600">
                                  <Check className="w-4 h-4" />
                                </div>
                              );
                            }

                            return (
                              <Button
                                size="sm"
                                onClick={() => handleAddTrack(track.spotify_uri)}
                                className={cn(
                                  "flex items-center gap-1 flex-shrink-0",
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
                            );
                          })()}
                        </div>
                      ))}
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

                {(isSearching || isSearchPending) && searchResults.length === 0 && (
                  <div className="flex items-center justify-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">Searching...</p>
                    </div>
                  </div>
                )}

                {!isSearching && !isSearchPending && searchResults.length === 0 && searchQuery && searchQuery.length >= 2 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="text-sm">No results found for "{searchQuery}"</p>
                  </div>
                )}

                {!searchQuery && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Search className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p className="text-sm">Start typing to search for tracks</p>
                  </div>
                )}
              </CardContent>
            </div>
          </div>
        </Card>

        {/* Right Column - Playlist */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Playlist Tracks ({tracks.length})</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  className="flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {tracks.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Music className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p>No tracks remaining. Try resetting or creating a new playlist.</p>
                </div>
              ) : (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={tracks.map(track => track.track_id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-2">
                      {tracks.map((track, index) => (
                        <SortableTrackItem
                          key={track.track_id}
                          track={track}
                          index={index}
                          onRemove={handleRemoveTrack}
                          isRemoving={removingTracks.has(track.track_id)}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              )}
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
          disabled={isFinalizing}
        >
          {isCompleted ? 'Done Editing' : 'Cancel'}
        </Button>
        {!isCompleted && (
          <Button
            onClick={handleFinalize}
            disabled={isFinalizing || tracks.length === 0}
            className="flex-1 flex items-center gap-2"
          >
            {isFinalizing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Finalizing...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Finalize Playlist ({tracks.length} tracks)
              </>
            )}
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