import { useEffect, useRef, useCallback, useState } from 'react';

interface UseInfiniteScrollOptions {
    threshold?: number; // Distance from bottom in pixels to trigger load
    rootMargin?: string; // Margin around the root element (overrides threshold)
}

export function useInfiniteScroll(
    callback: () => void,
    options: UseInfiniteScrollOptions = {}
) {
    const { threshold = 300, rootMargin } = options;
    const callbackRef = useRef(callback);
    const observerRef = useRef<IntersectionObserver | null>(null);
    const [element, setElement] = useState<HTMLDivElement | null>(null);

    // Keep callback ref up to date
    useEffect(() => {
        callbackRef.current = callback;
    }, [callback]);

    // Memoize the observer callback to prevent recreating the observer
    const handleIntersect = useCallback((entries: IntersectionObserverEntry[]) => {
        const [entry] = entries;

        if (entry.isIntersecting) {
            callbackRef.current();
        }
    }, []);

    // Set up observer when element is available
    useEffect(() => {
        if (!element) {
            return;
        }

        // Use rootMargin if provided, otherwise calculate from threshold
        const margin = rootMargin || `${threshold}px`;

        observerRef.current = new IntersectionObserver(handleIntersect, {
            root: null,
            rootMargin: margin,
            threshold: 0,
        });

        observerRef.current.observe(element);

        return () => {
            if (observerRef.current) {
                observerRef.current.disconnect();
            }
        };
    }, [element, threshold, rootMargin, handleIntersect]);

    // Return a callback ref instead of a ref object
    const ref = useCallback((node: HTMLDivElement | null) => {
        setElement(node);
    }, []);

    return ref;
}

