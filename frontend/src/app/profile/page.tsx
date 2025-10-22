'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { ProfileDashboard, ProfileHeader, ProfileStats } from '@/components/features/profile';
import { ProfileSkeleton } from '@/components/shared/LoadingStates';
import { useProfile } from '@/lib/hooks';
import { Suspense } from 'react';

function ProfilePageContent() {
  const { spotifyProfile, dashboardData, isLoading, isDashboardLoading } = useProfile();

  // Show skeleton while loading
  if (isLoading) {
    return <ProfileSkeleton />;
  }

  const stats = dashboardData?.stats;

  return (
    <div className="h-screen bg-gradient-to-br from-background to-muted p-2 sm:p-3 overflow-hidden">
      <div className="h-full max-w-7xl mx-auto flex flex-col">
        <ProfileHeader spotifyProfile={spotifyProfile} />
        <ProfileStats stats={stats} />
        <ProfileDashboard dashboardData={dashboardData} isDashboardLoading={isDashboardLoading} spotifyProfile={spotifyProfile} />
      </div>
    </div>
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
