'use client';

import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef, useEffect, useCallback, useState } from 'react';
import { cn } from '@/lib/utils';
import { Track } from '@/lib/types/track';

interface VirtualTrackListProps {
    tracks: Track[];
    itemHeight?: number;
    containerHeight?: number;
    className?: string;
    renderTrack: (track: Track, index: number, isFocused?: boolean) => React.ReactNode;
    onTrackFocus?: (index: number) => void;
    onTrackSelect?: (index: number) => void;
}

export function VirtualTrackList({
    tracks,
    itemHeight = 60,
    containerHeight = 400,
    className,
    renderTrack,
    onTrackFocus,
    onTrackSelect,
}: VirtualTrackListProps) {
    const parentRef = useRef<HTMLDivElement>(null);
    const [focusedIndex, setFocusedIndex] = useState<number>(-1);

    const virtualizer = useVirtualizer({
        count: tracks.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => itemHeight,
        overscan: 5, // Railway 5 items outside visible area for smoother scrolling
    });

    const scrollToIndex = useCallback((index: number) => {
        virtualizer.scrollToIndex(index, {
            align: 'center',
        });
    }, [virtualizer]);

    const handleKeyDown = useCallback((event: KeyboardEvent) => {
        if (!tracks.length) return;

        let newIndex = focusedIndex;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                newIndex = Math.min(focusedIndex + 1, tracks.length - 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                newIndex = Math.max(focusedIndex - 1, 0);
                break;
            case 'Home':
                event.preventDefault();
                newIndex = 0;
                break;
            case 'End':
                event.preventDefault();
                newIndex = tracks.length - 1;
                break;
            case 'Enter':
            case ' ':
                event.preventDefault();
                if (focusedIndex >= 0) {
                    onTrackSelect?.(focusedIndex);
                }
                return;
            default:
                return;
        }

        if (newIndex !== focusedIndex) {
            setFocusedIndex(newIndex);
            scrollToIndex(newIndex);
            onTrackFocus?.(newIndex);
        }
    }, [tracks.length, focusedIndex, scrollToIndex, onTrackFocus, onTrackSelect]);

    useEffect(() => {
        const container = parentRef.current;
        if (!container) return;

        container.addEventListener('keydown', handleKeyDown);
        return () => container.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    return (
        <div
            ref={parentRef}
            className={cn('overflow-auto focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2', className)}
            style={{ height: containerHeight }}
            tabIndex={0}
            role="listbox"
            aria-label="Track list"
        >
            <div
                style={{
                    height: `${virtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                }}
            >
                {virtualizer.getVirtualItems().map((virtualRow) => (
                    <div
                        key={virtualRow.key}
                        style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: `${virtualRow.size}px`,
                            transform: `translateY(${virtualRow.start}px)`,
                        }}
                        role="option"
                        aria-selected={focusedIndex === virtualRow.index}
                    >
                        {renderTrack(tracks[virtualRow.index], virtualRow.index, focusedIndex === virtualRow.index)}
                    </div>
                ))}
            </div>
        </div>
    );
}
