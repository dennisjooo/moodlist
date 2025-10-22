'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { MoodDistribution } from '@/lib/api/user';
import { Heart, Smile, Frown, Zap, Cloud } from 'lucide-react';

interface MoodDistributionChartProps {
    distribution: MoodDistribution[];
}

const getMoodIcon = (emotion: string) => {
    const lowerEmotion = emotion.toLowerCase();
    if (lowerEmotion.includes('happy') || lowerEmotion.includes('joy')) return Smile;
    if (lowerEmotion.includes('sad') || lowerEmotion.includes('melancholy')) return Frown;
    if (lowerEmotion.includes('energetic') || lowerEmotion.includes('excited')) return Zap;
    if (lowerEmotion.includes('calm') || lowerEmotion.includes('peaceful')) return Cloud;
    return Heart;
};

const getMoodColor = (emotion: string) => {
    const lowerEmotion = emotion.toLowerCase();
    if (lowerEmotion.includes('happy') || lowerEmotion.includes('joy')) return 'text-yellow-500';
    if (lowerEmotion.includes('sad') || lowerEmotion.includes('melancholy')) return 'text-blue-500';
    if (lowerEmotion.includes('energetic') || lowerEmotion.includes('excited')) return 'text-orange-500';
    if (lowerEmotion.includes('calm') || lowerEmotion.includes('peaceful')) return 'text-green-500';
    return 'text-pink-500';
};

const getMoodBgColor = (emotion: string) => {
    const lowerEmotion = emotion.toLowerCase();
    if (lowerEmotion.includes('happy') || lowerEmotion.includes('joy')) return 'bg-yellow-500/10';
    if (lowerEmotion.includes('sad') || lowerEmotion.includes('melancholy')) return 'bg-blue-500/10';
    if (lowerEmotion.includes('energetic') || lowerEmotion.includes('excited')) return 'bg-orange-500/10';
    if (lowerEmotion.includes('calm') || lowerEmotion.includes('peaceful')) return 'bg-green-500/10';
    return 'bg-pink-500/10';
};

const getMoodBarColor = (emotion: string) => {
    const lowerEmotion = emotion.toLowerCase();
    if (lowerEmotion.includes('happy') || lowerEmotion.includes('joy')) return 'bg-yellow-500';
    if (lowerEmotion.includes('sad') || lowerEmotion.includes('melancholy')) return 'bg-blue-500';
    if (lowerEmotion.includes('energetic') || lowerEmotion.includes('excited')) return 'bg-orange-500';
    if (lowerEmotion.includes('calm') || lowerEmotion.includes('peaceful')) return 'bg-green-500';
    return 'bg-pink-500';
};

export function MoodDistributionChart({ distribution }: MoodDistributionChartProps) {
    if (!distribution || distribution.length === 0) {
        return (
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center space-x-2 text-base">
                        <Heart className="w-4 h-4" />
                        <span>Mood Palette</span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground text-center py-6 text-sm">
                        No mood data yet. Create some playlists to see your mood patterns!
                    </p>
                </CardContent>
            </Card>
        );
    }

    const total = distribution.reduce((sum, item) => sum + item.count, 0);

    return (
        <Card className="lg:h-full flex flex-col">
            <CardHeader className="flex-shrink-0 pb-3">
                <CardTitle className="flex items-center space-x-2 text-base">
                    <Heart className="w-4 h-4" />
                    <span>Mood Palette</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="lg:flex-1 lg:overflow-y-auto lg:min-h-0 space-y-3 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-transparent hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/30">
                {distribution.map((item, index) => {
                    const Icon = getMoodIcon(item.emotion);
                    const percentage = (item.count / total) * 100;

                    return (
                        <div key={index} className="space-y-1">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-2 min-w-0">
                                    <div className={`p-1.5 rounded-lg ${getMoodBgColor(item.emotion)} flex-shrink-0`}>
                                        <Icon className={`w-3 h-3 ${getMoodColor(item.emotion)}`} />
                                    </div>
                                    <span className="text-sm font-medium capitalize truncate">{item.emotion}</span>
                                </div>
                                <span className="text-xs text-muted-foreground flex-shrink-0 ml-2">
                                    {item.count}
                                </span>
                            </div>
                            <div className="w-full bg-muted rounded-full h-1.5">
                                <div
                                    className={`h-1.5 rounded-full transition-all ${getMoodBarColor(item.emotion)}`}
                                    style={{ width: `${percentage}%` }}
                                />
                            </div>
                        </div>
                    );
                })}
            </CardContent>
        </Card>
    );
}

