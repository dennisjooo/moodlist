'use client';

import { Card } from '@/components/ui/card';
import { Music, User, TrendingUp } from 'lucide-react';
import { type UserStats } from '@/lib/api/user';

interface ProfileStatsProps {
    stats: UserStats | undefined;
}

export function ProfileStats({ stats }: ProfileStatsProps) {
    const statItems = [
        {
            icon: User,
            label: 'Moods Analyzed',
            value: stats?.moods_analyzed || 0,
            iconBg: 'bg-green-500/10',
            iconColor: 'text-green-600',
            valueColor: 'text-green-600'
        },
        {
            icon: Music,
            label: 'Saved to Spotify',
            value: stats?.saved_playlists || 0,
            iconBg: 'bg-primary/10',
            iconColor: 'text-primary',
            valueColor: 'text-primary'
        },
        {
            icon: TrendingUp,
            label: 'Active Sessions',
            value: stats?.total_sessions || 0,
            iconBg: 'bg-blue-500/10',
            iconColor: 'text-blue-600',
            valueColor: 'text-blue-600'
        }
    ];

    return (
        <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-2 sm:mb-3 flex-shrink-0">
            {statItems.map((item, index) => {
                const Icon = item.icon;
                return (
                    <Card key={index} className="p-2 sm:p-3">
                        <div className="flex items-center gap-2 sm:gap-3">
                            <div className={`${item.iconBg} rounded-lg flex items-center justify-center flex-shrink-0 p-2 self-stretch`}>
                                <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${item.iconColor}`} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-xs text-muted-foreground truncate">{item.label}</p>
                                <p className={`text-lg sm:text-xl font-bold ${item.valueColor} leading-tight`}>{item.value}</p>
                            </div>
                        </div>
                    </Card>
                );
            })}
        </div>
    );
}
