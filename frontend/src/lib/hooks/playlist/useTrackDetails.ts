import { useState, useRef } from 'react';
import { spotifyAPI, TrackDetails } from '@/lib/api/spotify';
import { logger } from '@/lib/utils/logger';

interface UseTrackDetailsResult {
    trackDetails: TrackDetails | null;
    isLoading: boolean;
    error: string | null;
    loadTrackDetails: (spotifyUri: string) => Promise<void>;
}

export function useTrackDetails(): UseTrackDetailsResult {
    const [trackDetails, setTrackDetails] = useState<TrackDetails | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const loadedUriRef = useRef<string | null>(null);

    const loadTrackDetails = async (spotifyUri: string) => {
        if (loadedUriRef.current === spotifyUri) return;

        setIsLoading(true);
        setError(null);

        try {
            const details = await spotifyAPI.getTrackDetails(spotifyUri);
            logger.debug('Track details loaded', { component: 'useTrackDetails', spotifyUri, details });
            setTrackDetails(details);
            loadedUriRef.current = spotifyUri;
        } catch (err) {
            logger.error('Failed to fetch track details', err, { component: 'useTrackDetails', spotifyUri });
            setError('Failed to load track details');
        } finally {
            setIsLoading(false);
        }
    };

    return {
        trackDetails,
        isLoading,
        error,
        loadTrackDetails
    };
}

