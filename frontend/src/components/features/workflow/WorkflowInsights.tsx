'use client';

import { Music, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { WorkflowState } from '@/lib/types/workflow';
import { isTerminalStatus } from '@/lib/utils/workflow';

interface WorkflowInsightsProps {
    status: WorkflowState['status'];
    moodAnalysis: WorkflowState['moodAnalysis'];
    recommendations: WorkflowState['recommendations'];
    metadata?: WorkflowState['metadata'];
    error: string | null;
}

const MUSIC_FACTS = [
    "Spotify has over 100 million tracks in its library!",
    "The average person listens to about 18 hours of music per week.",
    "Music can reduce stress and improve your mood instantly.",
    "Your heartbeat can sync to the rhythm of music you're listening to.",
    "Studies show music helps you focus and be more productive.",
    "The fastest tempo in classical music can reach over 200 BPM!",
    "Listening to music releases dopamine, the 'feel-good' hormone.",
    "90% of people report music helps them deal with emotions.",
    "Your music taste is as unique as your fingerprint.",
    "The right playlist can make your workout feel 15% easier!",
];

export function WorkflowInsights({ status, moodAnalysis, recommendations, metadata, error }: WorkflowInsightsProps) {
    const [currentFactIndex, setCurrentFactIndex] = useState(0);

    // Rotate fun facts every 6 seconds
    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentFactIndex((prev) => (prev + 1) % MUSIC_FACTS.length);
        }, 6000);
        return () => clearInterval(interval);
    }, []);

    // Don't show if terminal status or has error
    if (!status || isTerminalStatus(status) || error) {
        return null;
    }

    const getInsightContent = () => {
        switch (status) {
            case 'analyzing_mood':
                return (
                    <p className="text-sm text-foreground">
                        Analyzing your mood description and musical preferences...
                    </p>
                );

            case 'gathering_seeds':
                if (moodAnalysis?.primary_emotion) {
                    return (
                        <div className="space-y-1">
                            <p className="text-sm text-foreground">
                                Searching for tracks that match: <span className="font-medium">{moodAnalysis.primary_emotion}</span> vibes
                            </p>
                            {moodAnalysis.search_keywords && moodAnalysis.search_keywords.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {moodAnalysis.search_keywords.slice(0, 4).map((keyword, idx) => (
                                        <span key={idx} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                            {keyword}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                }
                return (
                    <p className="text-sm text-foreground">
                        Finding the perfect seed tracks to build your playlist...
                    </p>
                );

            case 'generating_recommendations':
                if (recommendations && recommendations.length > 0) {
                    return (
                        <p className="text-sm text-foreground flex items-center gap-2">
                            <Music className="w-3.5 h-3.5" />
                            <span>Found <span className="font-medium">{recommendations.length}</span> perfect tracks</span>
                        </p>
                    );
                }
                return (
                    <p className="text-sm text-foreground">
                        Handpicking tracks that perfectly match your vibe...
                    </p>
                );

            case 'evaluating_quality':
                return (
                    <div className="space-y-1.5">
                        {recommendations && recommendations.length > 0 && (
                            <p className="text-sm text-foreground flex items-center gap-2">
                                <Music className="w-3.5 h-3.5" />
                                <span>Evaluating <span className="font-medium">{recommendations.length}</span> tracks</span>
                            </p>
                        )}
                        <p className="text-sm text-muted-foreground">
                            Checking that every track flows perfectly together...
                        </p>
                    </div>
                );

            case 'optimizing_recommendations':
                return (
                    <div className="space-y-1.5">
                        {recommendations && recommendations.length > 0 && (
                            <p className="text-sm text-foreground flex items-center gap-2">
                                <Music className="w-3.5 h-3.5" />
                                <span>Refining <span className="font-medium">{recommendations.length}</span> tracks</span>
                            </p>
                        )}
                        {metadata?.iteration ? (
                            <p className="text-sm text-muted-foreground">
                                Optimization pass {metadata.iteration} - Making it even better!
                            </p>
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                Fine-tuning the playlist for the best flow...
                            </p>
                        )}
                    </div>
                );

            case 'ordering_playlist':
                return (
                    <div className="space-y-1.5">
                        {recommendations && recommendations.length > 0 && (
                            <p className="text-sm text-foreground flex items-center gap-2">
                                <Music className="w-3.5 h-3.5" />
                                <span>Arranging <span className="font-medium">{recommendations.length}</span> tracks</span>
                            </p>
                        )}
                        <p className="text-sm text-muted-foreground">
                            Creating an energy arc: beginning → build → peak → wind down → closure
                        </p>
                        {metadata?.ordering_strategy && (
                            <p className="text-xs text-muted-foreground">
                                Strategy: {metadata.ordering_strategy.strategy?.replace(/_/g, ' ')}
                            </p>
                        )}
                    </div>
                );

            case 'creating_playlist':
                return (
                    <p className="text-sm text-foreground">
                        Packaging {recommendations?.length || 0} tracks into your personal Spotify playlist...
                    </p>
                );

            case 'pending':
                return (
                    <p className="text-sm text-foreground">
                        Preparing your personalized playlist experience...
                    </p>
                );

            default:
                // Show fun fact for any other state
                return (
                    <p
                        key={currentFactIndex}
                        className="text-sm text-foreground animate-in fade-in duration-500"
                    >
                        {MUSIC_FACTS[currentFactIndex]}
                    </p>
                );
        }
    };

    return (
        <div className="rounded-lg bg-gradient-to-r from-primary/5 to-purple-500/5 p-2.5 sm:p-3 border border-primary/10 overflow-hidden">
            <div className="flex items-start gap-2">
                <Sparkles className="w-3.5 h-3.5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">What we&apos;re cooking:</p>
                    {getInsightContent()}
                </div>
            </div>
        </div>
    );
}

