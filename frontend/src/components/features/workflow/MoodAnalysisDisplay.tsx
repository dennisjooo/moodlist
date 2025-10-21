'use client';

import { Badge } from '@/components/ui/badge';
import type { WorkflowState } from '@/lib/contexts/WorkflowContext';

interface MoodAnalysisDisplayProps {
    moodAnalysis: WorkflowState['moodAnalysis'];
    moodPrompt?: string;
}

export function MoodAnalysisDisplay({ moodAnalysis, moodPrompt }: MoodAnalysisDisplayProps) {
    // Show mood analysis when available
    if (moodAnalysis) {
        return (
            <div className="space-y-3 rounded-lg bg-muted/30 p-3 sm:p-4 border border-border/50 overflow-hidden">
                <div className="flex items-start gap-2 overflow-hidden">
                    <div className="text-xl sm:text-2xl flex-shrink-0 mt-0.5">🎵</div>
                    <div className="flex-1 space-y-3 min-w-0 overflow-hidden">
                        <p className="text-sm font-medium text-foreground break-words leading-relaxed pr-2 [word-break:break-word] max-w-full">
                            {moodAnalysis.mood_interpretation}
                        </p>
                        {moodAnalysis.primary_emotion && (
                            <div className="flex items-center flex-wrap gap-2 text-xs text-muted-foreground pt-1">
                                <Badge variant="secondary" className="text-xs">
                                    {moodAnalysis.primary_emotion}
                                </Badge>
                                {moodAnalysis.energy_level && (
                                    <Badge variant="secondary" className="text-xs">
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

