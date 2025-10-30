'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { ProfileDashboard, ProfileHeader, ProfilePageLayout, ProfileStats } from '@/components/features/profile';
import { ProfileSkeleton } from '@/components/shared/LoadingStates';
import { CrossfadeTransition } from '@/components/ui/crossfade-transition';
import { useProfile } from '@/lib/hooks';
import { Suspense } from 'react';

function ProfilePageContent() {
  const { spotifyProfile, dashboardData, isLoading, isDashboardLoading } = useProfile();

  const stats = dashboardData?.stats;

  return (
    <ProfilePageLayout>
      <CrossfadeTransition
        isLoading={isLoading}
        skeleton={<ProfileSkeleton withLayout={false} />}
      >
        <div className="flex flex-1 flex-col">
          <section className="relative overflow-hidden rounded-3xl border border-border/60 bg-background/80 p-4 sm:p-6 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
            <div
              aria-hidden="true"
              className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/10 via-transparent to-transparent"
            />
            <div className="relative flex flex-col gap-4">
              <ProfileHeader spotifyProfile={spotifyProfile} />
              <ProfileStats stats={stats} />
            </div>
          </section>

          <section className="mt-6 flex-1 overflow-hidden rounded-3xl border border-border/60 bg-background/80 p-4 sm:p-6 shadow-[0_25px_60px_-30px_rgba(15,23,42,0.45)] backdrop-blur-xl">
            <div className="flex h-full flex-col">
              <div className="flex-1 min-h-0">
                <ProfileDashboard
                  dashboardData={dashboardData}
                  isDashboardLoading={isDashboardLoading}
                  spotifyProfile={spotifyProfile}
                />
              </div>
            </div>
          </section>
        </div>
      </CrossfadeTransition>
    </ProfilePageLayout>
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
