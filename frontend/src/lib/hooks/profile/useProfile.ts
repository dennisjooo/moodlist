import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/store/authStore';
import { spotifyAPI, type SpotifyProfile } from '@/lib/api/spotify';
import { userAPI, type DashboardData } from '@/lib/api/user';
import { logger } from '@/lib/utils/logger';

interface UseProfileReturn {
    spotifyProfile: SpotifyProfile | null;
    dashboardData: DashboardData | null;
    isLoading: boolean;
    isDashboardLoading: boolean;
    error: string | null;
}

export function useProfile(): UseProfileReturn {
    const router = useRouter();
    const { user, isAuthenticated } = useAuth();
    const [spotifyProfile, setSpotifyProfile] = useState<SpotifyProfile | null>(null);
    const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isDashboardLoading, setIsDashboardLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isAuthenticated && user) {
            fetchProfileData();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAuthenticated, user]);

    const fetchProfileData = async () => {
        if (!user) return;

        try {
            setIsLoading(true);
            setIsDashboardLoading(true);
            setError(null);

            // Fetch Spotify profile and dashboard data in parallel
            const [profileResponse, dashboard] = await Promise.allSettled([
                spotifyAPI.getProfile(),
                userAPI.getDashboard()
            ]);

            // Handle Spotify profile response
            if (profileResponse.status === 'fulfilled') {
                setSpotifyProfile(profileResponse.value);
            } else {
                if (profileResponse.reason.message?.includes('401')) {
                    router.push('/');
                    return;
                }
                logger.error('Failed to fetch Spotify profile', profileResponse.reason, { component: 'useProfile' });
                setError('Failed to load Spotify profile');
            }

            // Handle dashboard response
            if (dashboard.status === 'fulfilled') {
                setDashboardData(dashboard.value);
            } else {
                logger.error('Failed to fetch dashboard data', dashboard.reason, { component: 'useProfile' });
                setError(prev => prev || 'Failed to load dashboard data');
            }
        } catch (error) {
            logger.error('Error fetching profile data', error, { component: 'useProfile' });
            setError('An unexpected error occurred');
        } finally {
            setIsLoading(false);
            setIsDashboardLoading(false);
        }
    };

    return {
        spotifyProfile,
        dashboardData,
        isLoading,
        isDashboardLoading,
        error
    };
}
