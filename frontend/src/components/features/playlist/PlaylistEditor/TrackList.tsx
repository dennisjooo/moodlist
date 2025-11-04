'use client';

import type { Track } from '@/lib/types/workflow';
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
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Music } from 'lucide-react';
import { useCallback } from 'react';
import { TrackItem } from './TrackItem';

export interface TrackListProps {
    tracks: Track[];
    onReorder: (oldIndex: number, newIndex: number) => void;
    onRemove: (trackId: string) => void;
    removingTracks: Set<string>;
}

export function TrackList({ tracks, onReorder, onRemove, removingTracks }: TrackListProps) {
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

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            const oldIndex = tracks.findIndex((track) => track.track_id === active.id);
            const newIndex = tracks.findIndex((track) => track.track_id === over.id);

            if (oldIndex !== -1 && newIndex !== -1) {
                onReorder(oldIndex, newIndex);
            }
        }
    };

    const handleRemove = useCallback((trackId: string) => {
        onRemove(trackId);
    }, [onRemove]);

    if (tracks.length === 0) {
        return (
            <div className="text-center py-16 text-muted-foreground">
                <div className="relative inline-block">
                    <Music className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse" />
                    <div className="absolute inset-0 w-16 h-16 mx-auto bg-primary/5 rounded-full blur-xl animate-pulse" />
                </div>
                <p className="text-base font-medium">No tracks remaining</p>
                <p className="text-sm mt-1">Try resetting or creating a new playlist</p>
            </div>
        );
    }

    return (
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
                        <TrackItem
                            key={track.track_id}
                            track={track}
                            index={index}
                            onRemove={handleRemove}
                            isRemoving={removingTracks.has(track.track_id)}
                        />
                    ))}
                </div>
            </SortableContext>
        </DndContext>
    );
}

