'use client';

import { Badge } from '@/components/ui/badge';
import type { WorkflowState } from '@/lib/types/workflow';
import { useEffect, useState } from 'react';

interface MoodAnalysisDisplayProps {
    moodAnalysis: WorkflowState['moodAnalysis'];
    moodPrompt?: string;
}

export function MoodAnalysisDisplay({ moodAnalysis, moodPrompt }: MoodAnalysisDisplayProps) {
    const [showBadges, setShowBadges] = useState(false);

    // Animate badges appearing with a slight delay after the main text
    useEffect(() => {
        if (moodAnalysis) {
            const timer = setTimeout(() => setShowBadges(true), 300);
            return () => clearTimeout(timer);
        }
        setShowBadges(false);
    }, [moodAnalysis]);

    // Show mood analysis when available
    if (moodAnalysis) {
        return (
            <div className="space-y-2 rounded-lg bg-gradient-to-br from-primary/5 via-purple-500/5 to-primary/5 p-2.5 sm:p-3 border border-primary/20 overflow-hidden animate-in fade-in duration-500">
                <div className="flex items-start gap-2 overflow-hidden">
                    <div className="text-lg sm:text-xl flex-shrink-0 mt-0.5 animate-in zoom-in duration-300">🎵</div>
                    <div className="flex-1 space-y-2 min-w-0 overflow-hidden">
                        <p className="text-sm font-medium text-foreground break-words leading-relaxed pr-2 [word-break:break-word] max-w-full">
                            {moodAnalysis.mood_interpretation}
                        </p>
                        {moodAnalysis.primary_emotion && (
                            <div className="flex items-center flex-wrap gap-1.5 text-xs text-muted-foreground">
                                <Badge
                                    variant="secondary"
                                    className="text-xs animate-in slide-in-from-left duration-300"
                                    style={{
                                        animationDelay: showBadges ? '0ms' : '500ms',
                                        opacity: showBadges ? 1 : 0,
                                    }}
                                >
                                    {moodAnalysis.primary_emotion}
                                </Badge>
                                {moodAnalysis.energy_level && (
                                    <Badge
                                        variant="secondary"
                                        className="text-xs animate-in slide-in-from-left duration-300"
                                        style={{
                                            animationDelay: showBadges ? '100ms' : '600ms',
                                            opacity: showBadges ? 1 : 0,
                                        }}
                                    >
                                        {moodAnalysis.energy_level}
                                    </Badge>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    // Show mood prompt when no analysis yet
    if (moodPrompt) {
        return (
            <div className="text-sm">
                <span className="font-medium">Mood:</span> {moodPrompt}
            </div>
        );
    }

    return null;
}

