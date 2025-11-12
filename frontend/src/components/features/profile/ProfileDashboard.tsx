'use client';

import { AudioInsightsCard, MoodDistributionChart, QuickActions, RecentActivityTimeline } from '@/components/features/profile';
import { type DashboardData } from '@/lib/api/user';
import { type SpotifyProfile } from '@/lib/api/spotify';

interface ProfileDashboardProps {
    dashboardData: DashboardData | null;
    isDashboardLoading: boolean;
    spotifyProfile: SpotifyProfile | null;
}

export function ProfileDashboard({ dashboardData, isDashboardLoading, spotifyProfile }: ProfileDashboardProps) {
    return (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-2 sm:gap-3 overflow-hidden min-h-0">
            {/* Mobile: Scrollable container */}
            <div className="lg:hidden overflow-y-auto min-h-0 space-y-2 sm:space-y-3">
                <QuickActions spotifyProfile={spotifyProfile} />
                <RecentActivityTimeline
                    recentActivity={dashboardData?.recent_activity.slice(0, 3) || []}
                    isLoading={isDashboardLoading}
                />
                {dashboardData && (
                    <MoodDistributionChart distribution={dashboardData.mood_distribution} />
                )}
                {dashboardData && (
                    <AudioInsightsCard insights={dashboardData.audio_insights} />
                )}
            </div>

            {/* Desktop: Left Column - Takes 2/3 width */}
            <div className="hidden lg:flex lg:col-span-2 flex-col gap-3 overflow-hidden min-h-0">
                <div className={dashboardData?.recent_activity?.length ? "flex-1 min-h-0" : "flex-shrink-0"}>
                    <RecentActivityTimeline
                        recentActivity={dashboardData?.recent_activity || []}
                        enablePagination={true}
                        isLoading={isDashboardLoading}
                    />
                </div>

                {dashboardData && (
                    <div className="flex-shrink-0">
                        <AudioInsightsCard insights={dashboardData.audio_insights} />
                    </div>
                )}
            </div>

            {/* Desktop: Right Column - Takes 1/3 width */}
            <div className="hidden lg:flex flex-col gap-3 overflow-hidden min-h-0">
                <div className="flex-shrink-0">
                    <QuickActions spotifyProfile={spotifyProfile} />
                </div>

                {dashboardData && (
                    <div className="flex-1 min-h-0">
                        <MoodDistributionChart distribution={dashboardData.mood_distribution} />
                    </div>
                )}
            </div>
        </div>
    );
}
