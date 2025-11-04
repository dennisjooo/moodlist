'use client';

import { BackButton } from '@/components/shared';
import { useAuth } from '@/lib/contexts/AuthContext';
import { MapPin, User, Users } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { type SpotifyProfile } from '@/lib/api/spotify';

interface ProfileHeaderProps {
    spotifyProfile: SpotifyProfile | null;
}

export function ProfileHeader({ spotifyProfile }: ProfileHeaderProps) {
    const router = useRouter();
    const { user } = useAuth();

    const handleBack = () => {
        router.back();
    };

    return (
        <div className="flex items-center justify-between mb-2 sm:mb-3">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <BackButton
                    onClick={handleBack}
                    size="sm"
                    iconOnly
                    animated
                    className="h-8 w-8 sm:h-10 sm:w-10 p-0 flex-shrink-0"
                />
                {spotifyProfile?.images?.[0]?.url ? (
                    <Image
                        src={spotifyProfile.images[0].url}
                        alt={spotifyProfile.display_name}
                        width={32}
                        height={32}
                        className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex-shrink-0"
                    />
                ) : (
                    <div className="w-8 h-8 sm:w-10 sm:h-10 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                    </div>
                )}
                <div className="min-w-0">
                    <h1 className="text-sm sm:text-lg font-bold truncate">{user?.display_name}</h1>
                    <p className="text-xs text-muted-foreground hidden sm:block">Dashboard</p>
                </div>
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
