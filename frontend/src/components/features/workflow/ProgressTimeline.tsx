'use client';

import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { useEffect } from 'react';
import { WORKFLOW_STAGES } from './workflowStageConfig';

interface ProgressTimelineProps {
    status: string | null;
}

export function ProgressTimeline({ status }: ProgressTimelineProps) {
    // Debug: Log when status prop changes
    useEffect(() => {
        logger.debug('ProgressTimeline status prop changed', {
            to: status,
        });
    }, [status]);

    const getCurrentStageIndex = (status: string | null): number => {
        if (!status) return 0;

        // Check each stage from most specific to least specific
        // This ensures that longer/more specific stage names are matched first
        for (let i = WORKFLOW_STAGES.length - 1; i >= 0; i--) {
            if (status.includes(WORKFLOW_STAGES[i].key)) {
                logger.debug('ProgressTimeline matched stage', {
                    status,
                    matchedStage: WORKFLOW_STAGES[i].key,
                    stageIndex: i,
                    stageLabel: WORKFLOW_STAGES[i].label
                });
                return i;
            }
        }

        logger.debug('ProgressTimeline no stage matched', { status });
        return 0;
    };

    const getVisibleStages = () => {
        const currentIndex = getCurrentStageIndex(status);
        const windowSize = 4;
        const totalStages = WORKFLOW_STAGES.length;

        // Strategy: Smooth progression where dot never goes backwards
        // Keep active stage at position 2 (middle-ish) as much as possible
        // Stages 0-1: dot progresses from 0->1 (show stages 0-3)
        // Stages 2-4: dot stays at position 2 (window slides: 0-3, 1-4, 2-5)
        // Stages 5-6: dot progresses to 2->3 (show stages 3-6)

        if (currentIndex === 0) {
            // Stage 0: show stages 0-3, dot at position 0
            return WORKFLOW_STAGES.slice(0, windowSize);
        } else if (currentIndex === 1) {
            // Stage 1: show stages 0-3, dot at position 1
            return WORKFLOW_STAGES.slice(0, windowSize);
        } else if (currentIndex >= totalStages - 2) {
            // Last 2 stages: show last 4, dot progresses to positions 2->3
            const startIndex = totalStages - windowSize;
            return WORKFLOW_STAGES.slice(startIndex);
        } else {
            // Middle stages: keep dot at position 2, slide the window
            const startIndex = currentIndex - 2;
            return WORKFLOW_STAGES.slice(startIndex, startIndex + windowSize);
        }
    };

    const visibleStages = getVisibleStages();
    const currentStageIndex = getCurrentStageIndex(status);

    logger.debug('ProgressTimeline render state', {
        status,
        currentStageIndex,
        visibleStages: visibleStages.map((s, i) => ({
            index: i,
            key: s.key,
            label: s.label,
            globalIndex: WORKFLOW_STAGES.findIndex(ws => ws.key === s.key)
        }))
    });

    return (
        <div className="relative">
            <div className="flex items-center justify-between px-2 py-2 rounded-lg bg-gradient-to-r from-muted/30 to-muted/10 backdrop-blur-sm border border-border/50">
                {visibleStages.map((stage, index) => {
                    const stageGlobalIndex = WORKFLOW_STAGES.findIndex(s => s.key === stage.key);
                    const isCurrentStage = stageGlobalIndex === currentStageIndex;
                    const isLastStage = index === visibleStages.length - 1;

                    return (
                        <div key={stage.key} className={cn(
                            "flex items-center",
                            !isLastStage && "flex-1"
                        )}>
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
                            {!isLastStage && (
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

