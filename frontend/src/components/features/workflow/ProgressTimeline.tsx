'use client';

import { cn } from '@/lib/utils';

interface ProgressTimelineProps {
    status: string | null;
}

const WORKFLOW_STAGES = [
    { key: 'analyzing_mood', label: 'Analyzing mood' },
    { key: 'gathering_seeds', label: 'Finding seeds' },
    { key: 'generating_recommendations', label: 'Generating playlist' },
    { key: 'evaluating_quality', label: 'Evaluating' },
    { key: 'optimizing_recommendations', label: 'Optimizing' },
    { key: 'creating_playlist', label: 'Creating playlist' },
    { key: 'completed', label: 'Complete' },
];

export function ProgressTimeline({ status }: ProgressTimelineProps) {
    const getCurrentStageIndex = (status: string | null): number => {
        if (!status) return 0;
        const index = WORKFLOW_STAGES.findIndex(stage => status.includes(stage.key));
        return index >= 0 ? index : 0;
    };

    const getVisibleStages = () => {
        const currentIndex = getCurrentStageIndex(status);
        const startIndex = Math.max(0, currentIndex - 2);
        const endIndex = currentIndex + 1;
        return WORKFLOW_STAGES.slice(startIndex, endIndex);
    };

    const visibleStages = getVisibleStages();

    return (
        <div className="relative">
            <div className="flex items-center justify-between px-2 py-3 rounded-lg bg-gradient-to-r from-muted/30 to-muted/10 backdrop-blur-sm border border-border/50">
                {visibleStages.map((stage, index) => {
                    const isCurrentStage = status?.includes(stage.key);

                    return (
                        <div key={stage.key} className="flex items-center flex-1">
                            <div className="relative flex items-center justify-center">
                                {/* Glow effect for current stage */}
                                {isCurrentStage && (
                                    <div className="absolute w-6 h-6 bg-primary/20 rounded-full animate-ping" />
                                )}
                                {/* Main dot */}
                                <div
                                    className={cn(
                                        "rounded-full transition-all duration-500 relative z-10",
                                        isCurrentStage
                                            ? "w-4 h-4 bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/50 ring-2 ring-primary/30 ring-offset-2 ring-offset-background"
                                            : "w-2.5 h-2.5 bg-gradient-to-br from-muted-foreground/60 to-muted-foreground/40"
                                    )}
                                />
                            </div>
                            {index < visibleStages.length - 1 && (
                                <div className={cn(
                                    "h-0.5 flex-1 rounded-full transition-all duration-300 ml-2",
                                    isCurrentStage
                                        ? "bg-gradient-to-r from-primary/60 to-muted-foreground/20"
                                        : "bg-muted-foreground/20"
                                )} />
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

