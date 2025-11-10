'use client';

import { type SpotifyProfile } from '@/lib/api/spotify';
import { useAuth } from '@/lib/store/authStore';
import { MapPin, Users } from 'lucide-react';

interface ProfileHeaderProps {
    spotifyProfile: SpotifyProfile | null;
}

export function ProfileHeader({ spotifyProfile }: ProfileHeaderProps) {
    const { user } = useAuth();

    return (
        <div className="flex items-center justify-between mb-2 sm:mb-3">
            <div className="min-w-0">
                    <h1 className="text-sm sm:text-lg font-bold truncate">Dashboard</h1>
                    <p className="text-xs text-muted-foreground hidden sm:block">Displaying stats for @{user?.display_name}</p>
                </div>

            {/* Compact User Info - Hidden on mobile */}
            <div className="hidden sm:flex items-center gap-4 text-xs text-muted-foreground flex-shrink-0">
                {spotifyProfile?.country && (
                    <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5" />
                        <span>{spotifyProfile.country}</span>
                    </div>
                )}
                <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5" />
                    <span>{spotifyProfile?.followers.toLocaleString() || 0}</span>
                </div>
            </div>
        </div>
    );
}
