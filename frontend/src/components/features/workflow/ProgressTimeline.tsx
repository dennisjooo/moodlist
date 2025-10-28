'use client';

import { cn } from '@/lib/utils';
import { logger } from '@/lib/utils/logger';
import { useEffect, type ComponentType } from 'react';
import { Brain, Music, Sparkles, Check, Zap } from 'lucide-react';

interface ProgressTimelineProps {
    status: string | null;
    currentStep?: string;
}

interface WorkflowStage {
    key: string;
    label: string;
    description: string;
    icon: ComponentType<{ className?: string }>;
}

const WORKFLOW_STAGES: WorkflowStage[] = [
    { 
        key: 'analyzing_mood', 
        label: 'Understanding', 
        description: 'Analyzing your request...',
        icon: Brain 
    },
    { 
        key: 'gathering_seeds', 
        label: 'Discovering', 
        description: 'Finding anchor tracks...',
        icon: Music 
    },
    { 
        key: 'generating_recommendations', 
        label: 'Generating', 
        description: 'Curating recommendations...',
        icon: Sparkles 
    },
    { 
        key: 'evaluating_quality', 
        label: 'Refining', 
        description: 'Ensuring quality...',
        icon: Zap 
    },
    { 
        key: 'completed', 
        label: 'Complete', 
        description: 'Your playlist is ready!',
        icon: Check 
    },
];

export function ProgressTimeline({ status, currentStep }: ProgressTimelineProps) {
    // Debug: Log when status prop changes
    useEffect(() => {
        logger.debug('ProgressTimeline status prop changed', {
            to: status,
            step: currentStep
        });
    }, [status, currentStep]);

    const getCurrentStageIndex = (status: string | null): number => {
        if (!status) return 0;
        const index = WORKFLOW_STAGES.findIndex(stage => status.includes(stage.key));
        return index >= 0 ? index : 0;
    };

    const isStageComplete = (stageIndex: number, currentIndex: number) => {
        return stageIndex < currentIndex;
    };

    const currentIndex = getCurrentStageIndex(status);

    return (
        <div className="relative space-y-3">
            {/* Progress bar */}
            <div className="flex items-center gap-2">
                {WORKFLOW_STAGES.map((stage, index) => {
                    const isCurrentStage = index === currentIndex;
                    const isComplete = isStageComplete(index, currentIndex);
                    const Icon = stage.icon;

                    return (
                        <div key={stage.key} className="flex items-center flex-1">
                            <div className="relative flex flex-col items-center gap-1.5 flex-1">
                                {/* Icon container */}
                                <div className="relative flex items-center justify-center">
                                    {/* Glow effect for current stage */}
                                    {isCurrentStage && (
                                        <div className="absolute w-8 h-8 bg-primary/20 rounded-full animate-ping" />
                                    )}
                                    {/* Main icon */}
                                    <div
                                        className={cn(
                                            "rounded-full transition-all duration-500 relative z-10 flex items-center justify-center",
                                            isCurrentStage
                                                ? "w-8 h-8 bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/50 ring-2 ring-primary/30 ring-offset-2 ring-offset-background"
                                                : isComplete
                                                ? "w-6 h-6 bg-gradient-to-br from-primary/60 to-primary/40"
                                                : "w-6 h-6 bg-gradient-to-br from-muted-foreground/40 to-muted-foreground/20"
                                        )}
                                    >
                                        <Icon className={cn(
                                            "transition-all duration-500",
                                            isCurrentStage ? "w-4 h-4 text-primary-foreground" :
                                            isComplete ? "w-3 h-3 text-primary-foreground" :
                                            "w-3 h-3 text-muted-foreground"
                                        )} />
                                    </div>
                                </div>
                                
                                {/* Label */}
                                <span className={cn(
                                    "text-xs font-medium transition-all duration-300 text-center whitespace-nowrap",
                                    isCurrentStage ? "text-foreground" :
                                    isComplete ? "text-muted-foreground" :
                                    "text-muted-foreground/60"
                                )}>
                                    {stage.label}
                                </span>
                            </div>
                            
                            {/* Connector line */}
                            {index < WORKFLOW_STAGES.length - 1 && (
                                <div className={cn(
                                    "h-0.5 flex-1 rounded-full transition-all duration-500 -mx-1",
                                    isComplete
                                        ? "bg-gradient-to-r from-primary/60 to-primary/40"
                                        : isCurrentStage
                                        ? "bg-gradient-to-r from-primary/40 to-muted-foreground/20"
                                        : "bg-muted-foreground/20"
                                )} />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Current stage description */}
            {currentIndex >= 0 && currentIndex < WORKFLOW_STAGES.length && (
                <div className="text-center">
                    <p className="text-sm text-muted-foreground animate-in fade-in duration-300">
                        {WORKFLOW_STAGES[currentIndex].description}
                    </p>
                    {currentStep && (
                        <p className="text-xs text-muted-foreground/70 mt-1 animate-in fade-in duration-300">
                            {formatCurrentStep(currentStep)}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function formatCurrentStep(step?: string) {
    if (!step) return '';
    const normalized = step
        .replace(/[_-]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

