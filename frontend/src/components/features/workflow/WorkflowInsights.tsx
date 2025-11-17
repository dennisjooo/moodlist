'use client';

import { Sparkles } from 'lucide-react';
import type { WorkflowState } from '@/lib/types/workflow';
import { MUSIC_FACTS } from '@/lib/constants/music';
import { useWorkflowInsights } from '@/lib/hooks/workflow';
import { ScrollArea } from '@/components/ui/scroll-area';

interface WorkflowInsightsProps {
    status: WorkflowState['status'];
    currentStep?: string | null;
    moodAnalysis: WorkflowState['moodAnalysis'];
    recommendations: WorkflowState['recommendations'];
    anchorTracks?: WorkflowState['anchorTracks'];
    metadata?: WorkflowState['metadata'];
    error: string | null;
}

export function WorkflowInsights({
    status,
    currentStep,
    moodAnalysis,
    recommendations,
    anchorTracks,
    metadata,
    error,
}: WorkflowInsightsProps) {
    const { events, timeFormatter, hasEvents } = useWorkflowInsights({
        status,
        currentStep,
        moodAnalysis,
        recommendations,
        anchorTracks,
        metadata,
        error,
    });

    return (
        <div className="rounded-lg bg-gradient-to-r from-primary/5 to-purple-500/5 p-2.5 sm:p-3 border border-primary/10 overflow-hidden">
            <div className="flex items-start gap-2">
                <Sparkles className="w-3.5 h-3.5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-[0.22em]">
                        What we&apos;re cooking
                    </p>

                    {!hasEvents && (
                        <div className="text-sm text-muted-foreground animate-in fade-in duration-500">
                            {MUSIC_FACTS[0]}
                        </div>
                    )}

                    {hasEvents && (
                        <ScrollArea className="h-[240px]">
                            <div className="space-y-2 pr-4">
                                {events.map(event => (
                                    <div
                                        key={event.id}
                                        className="flex items-start gap-2 rounded-lg bg-background/60 p-2 border border-border/40"
                                    >
                                        <div className="mt-0.5">{event.icon}</div>
                                        <div className="flex-1 min-w-0 space-y-0.5">
                                            <div className="flex items-center justify-between gap-2">
                                                <p className="text-sm font-medium text-foreground truncate">
                                                    {event.label}
                                                </p>
                                                <span className="text-[10px] text-muted-foreground/70">
                                                    {timeFormatter.format(event.timestamp)}
                                                </span>
                                            </div>
                                            {event.detail && (
                                                <p className="text-xs text-muted-foreground leading-relaxed">
                                                    {event.detail}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    )}
                </div>
            </div>
        </div>
    );
}

