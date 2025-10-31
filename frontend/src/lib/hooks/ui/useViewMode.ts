import { useEffect, useState } from 'react';

export type ViewMode = 'grid' | 'list';

/**
 * Hook for managing view mode with localStorage persistence
 * @param storageKey - The localStorage key to use for persistence
 * @param defaultMode - The default view mode if none is stored
 * @returns [viewMode, setViewMode] tuple
 */
export function useViewMode(
    storageKey: string = 'viewMode',
    defaultMode: ViewMode = 'grid'
): [ViewMode, (mode: ViewMode) => void] {
    const [viewMode, setViewMode] = useState<ViewMode>(defaultMode);

    // Load view mode from localStorage on mount (client-side only)
    useEffect(() => {
        const saved = localStorage.getItem(storageKey);
        if (saved === 'grid' || saved === 'list') {
            setViewMode(saved);
        }
    }, [storageKey]);

    // Save view mode to localStorage whenever it changes
    useEffect(() => {
        localStorage.setItem(storageKey, viewMode);
    }, [viewMode, storageKey]);

    return [viewMode, setViewMode];
}

