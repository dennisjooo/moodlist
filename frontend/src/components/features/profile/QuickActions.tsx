'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type SpotifyProfile } from '@/lib/api/spotify';
import { ExternalLink, List, Plus, TrendingUp } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface QuickActionsProps {
    spotifyProfile: SpotifyProfile | null;
}

export function QuickActions({ spotifyProfile }: QuickActionsProps) {
    const router = useRouter();

    const actions = [
        {
            icon: Plus,
            label: 'Create Playlist',
            description: 'Generate a new mood-based playlist',
            onClick: () => router.push('/create'),
            variant: 'default' as const,
            className: 'bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70'
        },
        {
            icon: ExternalLink,
            label: 'View Spotify Profile',
            description: 'Open your Spotify profile',
            onClick: () => {
                if (spotifyProfile?.id) {
                    window.open(`https://open.spotify.com/user/${spotifyProfile.id}`, '_blank');
                }
            },
            variant: 'outline' as const
        }
    ];

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-base">
                    <TrendingUp className="w-4 h-4" />
                    <span>Quick Actions</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
                {actions.map((action, index) => {
                    const Icon = action.icon;
                    return (
                        <Button
                            key={index}
                            variant={action.variant}
                            className={`w-full justify-start h-auto py-3 px-3 touch-manipulation ${action.className || ''}`}
                            onClick={action.onClick}
                        >
                            <div className="flex items-center gap-2 w-full">
                                <Icon className="w-4 h-4 flex-shrink-0" />
                                <div className="text-left min-w-0">
                                    <div className="font-semibold text-sm">{action.label}</div>
                                    <div className="text-xs opacity-80 font-normal truncate">{action.description}</div>
                                </div>
                            </div>
                        </Button>
                    );
                })}
            </CardContent>
        </Card>
    );
}

