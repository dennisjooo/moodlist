'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AudioInsights } from '@/lib/api/user';
import { Radio, TrendingUp, Activity, BarChart3 } from 'lucide-react';

interface AudioInsightsCardProps {
    insights: AudioInsights;
}

const getFeatureLabel = (value: number) => {
    if (value >= 0.7) return 'High';
    if (value >= 0.4) return 'Medium';
    return 'Low';
};

const getFeatureColor = (value: number) => {
    if (value >= 0.7) return 'text-green-600';
    if (value >= 0.4) return 'text-yellow-600';
    return 'text-blue-600';
};

export function AudioInsightsCard({ insights }: AudioInsightsCardProps) {
    const features = [
        {
            name: 'Energy',
            value: insights.avg_energy,
            icon: Activity,
            description: 'Intensity and activity level'
        },
        {
            name: 'Valence',
            value: insights.avg_valence,
            icon: TrendingUp,
            description: 'Musical positiveness'
        },
        {
            name: 'Danceability',
            value: insights.avg_danceability,
            icon: Radio,
            description: 'Suitability for dancing'
        }
    ];

    const totalEnergy = Object.values(insights.energy_distribution).reduce((a, b) => a + b, 0);

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-base">
                    <BarChart3 className="w-4 h-4" />
                    <span>Audio Insights</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                    {features.map((feature) => {
                        const Icon = feature.icon;
                        const percentage = feature.value * 100;

                        return (
                            <div key={feature.name} className="space-y-1">
                                <div className="flex items-center gap-1">
                                    <Icon className="w-3 h-3 text-muted-foreground" />
                                    <span className="text-xs font-medium">{feature.name}</span>
                                </div>
                                <div className="text-right">
                                    <span className={`text-lg font-bold ${getFeatureColor(feature.value)}`}>
                                        {getFeatureLabel(feature.value)}
                                    </span>
                                </div>
                                <div className="w-full bg-muted rounded-full h-1.5">
                                    <div
                                        className="h-1.5 rounded-full bg-gradient-to-r from-primary/50 to-primary transition-all"
                                        style={{ width: `${percentage}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>

                {totalEnergy > 0 && (
                    <div className="pt-3 border-t">
                        <div className="grid grid-cols-3 gap-2">
                            {Object.entries(insights.energy_distribution).map(([level, count]) => {
                                const levelPercentage = totalEnergy > 0 ? (count / totalEnergy) * 100 : 0;
                                const levelColors = {
                                    high: 'bg-red-500/10 text-red-600 border-red-200/50',
                                    medium: 'bg-yellow-500/10 text-yellow-600 border-yellow-200/50',
                                    low: 'bg-blue-500/10 text-blue-600 border-blue-200/50'
                                };

                                return (
                                    <div
                                        key={level}
                                        className={`p-2 rounded-lg border text-center ${levelColors[level as keyof typeof levelColors]}`}
                                    >
                                        <div className="text-lg font-bold">{count}</div>
                                        <div className="text-xs capitalize">{level}</div>
                                        <div className="text-xs opacity-75">{levelPercentage.toFixed(0)}%</div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

