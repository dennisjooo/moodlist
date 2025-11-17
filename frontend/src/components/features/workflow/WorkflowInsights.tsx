'use client';

import { Activity, Compass, ListMusic, Music, Sparkles, TrendingUp } from 'lucide-react';
import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { WorkflowState } from '@/lib/types/workflow';
import { isTerminalStatus } from '@/lib/utils/workflow';
import { MUSIC_FACTS } from '@/lib/constants/music';

interface WorkflowInsightsProps {
    status: WorkflowState['status'];
    currentStep?: string | null;
    moodAnalysis: WorkflowState['moodAnalysis'];
    recommendations: WorkflowState['recommendations'];
    anchorTracks?: WorkflowState['anchorTracks'];
    metadata?: WorkflowState['metadata'];
    error: string | null;
}

type LogEntry = {
    id: string;
    label: string;
    detail?: string;
    icon: ReactNode;
    timestamp: Date;
};

const MAX_EVENT_HISTORY = 6;

function formatStep(step?: string | null): string | undefined {
    if (!step) return undefined;
    return step.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
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
    const [events, setEvents] = useState<LogEntry[]>([]);
    const prevStatusRef = useRef<string | null>(null);
    const prevRecoCountRef = useRef(0);
    const prevAnchorCountRef = useRef(0);
    const prevIterationRef = useRef<number | undefined>(undefined);
    const moodLoggedRef = useRef(false);
    const eventIdRef = useRef(0);

    const recommendationCount = recommendations?.length ?? 0;
    const anchorCount = anchorTracks?.length ?? 0;
    const iterationValue = metadata?.iteration;
    const primaryEmotion = moodAnalysis?.primary_emotion;

    const timeFormatter = useMemo(() => new Intl.DateTimeFormat(undefined, {
        hour: 'numeric',
        minute: '2-digit',
    }), []);

    const getStatusEvent = useCallback((currentStatus: string): { label: string; detail?: string; icon: ReactNode } => {
        const normalized = currentStatus.toLowerCase();
        if (normalized.includes('analyzing_mood')) {
            return {
                label: 'Analyzing your vibe',
                detail: 'Reading between the lines of your mood prompt',
                icon: <Sparkles className="w-3.5 h-3.5 text-purple-500" />,
            };
        }
        if (normalized.includes('gathering_seeds')) {
            return {
                label: 'Gathering musical seeds',
                detail: 'Searching through influences and favorite artists',
                icon: <Compass className="w-3.5 h-3.5 text-amber-500" />,
            };
        }
        if (normalized.includes('generating_recommendations')) {
            return {
                label: 'Spinning up recommendations',
                detail: 'Matching tracks that mirror your vibe',
                icon: <Music className="w-3.5 h-3.5 text-primary" />,
            };
        }
        if (normalized.includes('evaluating_quality')) {
            return {
                label: 'Evaluating the flow',
                detail: 'Scoring transitions and cohesion',
                icon: <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />,
            };
        }
        if (normalized.includes('optimizing_recommendations')) {
            return {
                label: 'Polishing the setlist',
                detail: 'Iterating to nudge scores even higher',
                icon: <Sparkles className="w-3.5 h-3.5 text-sky-500" />,
            };
        }
        if (normalized.includes('ordering_playlist')) {
            return {
                label: 'Sequencing the playlist',
                detail: 'Shaping the energy arc from start to finish',
                icon: <ListMusic className="w-3.5 h-3.5 text-rose-500" />,
            };
        }
        if (normalized.includes('creating_playlist')) {
            return {
                label: 'Saving to Spotify',
                detail: 'Packaging everything into your playlist',
                icon: <Music className="w-3.5 h-3.5 text-primary" />,
            };
        }
        return {
            label: 'In progress',
            detail: 'Keeping the beat moving',
            icon: <Activity className="w-3.5 h-3.5 text-primary" />,
        };
    }, []);

    const resetHistory = () => {
        setEvents([]);
        prevStatusRef.current = null;
        prevRecoCountRef.current = 0;
        prevAnchorCountRef.current = 0;
        prevIterationRef.current = undefined;
        moodLoggedRef.current = false;
        eventIdRef.current = 0;
    };

    // Reset when workflow ends or errors
    useEffect(() => {
        if (!status || isTerminalStatus(status) || error) {
            resetHistory();
        }
    }, [status, error]);

    useEffect(() => {
        if (!status || isTerminalStatus(status) || error) {
            return;
        }

        const entries: LogEntry[] = [];
        const pushEvent = (label: string, detail: string | undefined, icon: ReactNode) => {
            eventIdRef.current += 1;
            entries.push({
                id: `${eventIdRef.current}`,
                label,
                detail,
                icon,
                timestamp: new Date(),
            });
        };

        // Status change events
        if (status !== prevStatusRef.current) {
            const { label, detail, icon } = getStatusEvent(status);
            const enrichedDetail = formatStep(currentStep) || detail;
            pushEvent(label, enrichedDetail, icon);
        }

        // Mood analysis ready
        if (!moodLoggedRef.current && primaryEmotion) {
            pushEvent(
                'Mood decoded',
                `Primary emotion: ${primaryEmotion}`,
                <Sparkles className="w-3.5 h-3.5 text-purple-500" />
            );
            moodLoggedRef.current = true;
        }

        // Anchor tracks locked in
        if (anchorCount > prevAnchorCountRef.current) {
            const diff = anchorCount - prevAnchorCountRef.current;
            const anchors = anchorTracks?.slice(prevAnchorCountRef.current, anchorCount) ?? [];
            const anchorPreview = anchors
                .map(track => track.name)
                .filter(Boolean)
                .slice(0, 2)
                .join(', ');
            const detail = anchorPreview
                ? `Secured ${diff} anchor ${diff > 1 ? 'tracks' : 'track'} (${anchorPreview}${anchorCount > 2 ? '…' : ''})`
                : `Secured ${diff} new anchor ${diff > 1 ? 'tracks' : 'track'}`;
            pushEvent(
                'Anchors locked',
                detail,
                <Compass className="w-3.5 h-3.5 text-amber-500" />
            );
        }

        // Recommendations arriving
        if (recommendationCount > prevRecoCountRef.current) {
            const diff = recommendationCount - prevRecoCountRef.current;
            pushEvent(
                `Added ${diff} track${diff === 1 ? '' : 's'}`,
                `Now at ${recommendationCount} curated pick${recommendationCount === 1 ? '' : 's'}`,
                <Music className="w-3.5 h-3.5 text-primary" />
            );
        }

        // Optimization iterations
        if (iterationValue && iterationValue !== prevIterationRef.current) {
            pushEvent(
                `Optimization pass ${iterationValue}`,
                'Fine-tuning for cohesion and flow',
                <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
            );
        }

        if (entries.length > 0) {
            setEvents(prev => {
                const next = [...entries, ...prev];
                return next.slice(0, MAX_EVENT_HISTORY);
            });
        }

        prevStatusRef.current = status;
        prevRecoCountRef.current = recommendationCount;
        prevAnchorCountRef.current = anchorCount;
        prevIterationRef.current = iterationValue;
    }, [
        status,
        currentStep,
        recommendationCount,
        anchorCount,
        iterationValue,
        primaryEmotion,
        anchorTracks,
        error,
        getStatusEvent,
    ]);

    // If we have no events yet, show a friendly placeholder
    const hasEvents = events.length > 0;

    return (
        <div className="rounded-lg bg-gradient-to-r from-primary/5 to-purple-500/5 p-2.5 sm:p-3 border border-primary/10 overflow-hidden">
            <div className="flex items-start gap-2">
                <Sparkles className="w-3.5 h-3.5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-[0.22em]">What we&apos;re cooking</p>

                    {!hasEvents && (
                        <div className="text-sm text-muted-foreground animate-in fade-in duration-500">
                            {MUSIC_FACTS[0]}
                        </div>
                    )}

                    {hasEvents && (
                        <div className="space-y-2">
                            {events.map(event => (
                                <div key={event.id} className="flex items-start gap-2 rounded-lg bg-background/60 p-2 border border-border/40">
                                    <div className="mt-0.5">
                                        {event.icon}
                                    </div>
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
                    )}
                </div>
            </div>
        </div>
    );
}

