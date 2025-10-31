import { useEffect, useState } from 'react';

/**
 * Hook for managing search input with debouncing
 * @param initialValue - Initial search value
 * @param onDebouncedChange - Callback when debounced value changes
 * @param delay - Debounce delay in milliseconds (default: 300)
 * @returns [searchValue, setSearchValue, debouncedValue] tuple
 */
export function useDebouncedSearch(
    initialValue: string = '',
    onDebouncedChange?: (value: string) => void,
    delay: number = 300
): [string, (value: string) => void, string] {
    const [searchValue, setSearchValue] = useState(initialValue);
    const [debouncedValue, setDebouncedValue] = useState(initialValue);

    // Update local state when initial value changes (e.g., filters reset)
    useEffect(() => {
        setSearchValue(initialValue);
    }, [initialValue]);

    // Debounce the search value
    useEffect(() => {
        const timeout = window.setTimeout(() => {
            setDebouncedValue(searchValue);
            onDebouncedChange?.(searchValue);
        }, delay);

        return () => {
            window.clearTimeout(timeout);
        };
    }, [searchValue, onDebouncedChange, delay]);

    return [searchValue, setSearchValue, debouncedValue];
}

