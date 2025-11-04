'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { ProfileDashboard, ProfileHeader, ProfileStats } from '@/components/features/profile';
import { ProfileSkeleton } from '@/components/shared/LoadingStates';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import Navigation from '@/components/layout/Navigation/Navigation';
import { useProfile } from '@/lib/hooks';
import { Suspense } from 'react';

function ProfilePageContent() {
  const { spotifyProfile, dashboardData, isLoading, isDashboardLoading } = useProfile();

  const stats = dashboardData?.stats;

  return (
    <>
      <Navigation />
      <CrossfadeTransition
        isLoading={isLoading}
        skeleton={<ProfileSkeleton />}
      >
        <div className="h-screen pt-2 sm:pt-3 px-2 sm:px-3 overflow-hidden">
          <div className="h-full max-w-7xl mx-auto flex flex-col">
            <ProfileHeader spotifyProfile={spotifyProfile} />
            <ProfileStats stats={stats} />
            <ProfileDashboard dashboardData={dashboardData} isDashboardLoading={isDashboardLoading} spotifyProfile={spotifyProfile} />
          </div>
        </div>
      </CrossfadeTransition>
    </>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <AuthGuard optimistic={false}>
        <ProfilePageContent />
      </AuthGuard>
    </Suspense>
  );
}
