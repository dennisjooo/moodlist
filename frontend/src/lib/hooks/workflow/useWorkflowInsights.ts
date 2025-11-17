import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { WorkflowState } from '@/lib/types/workflow';
import { isTerminalStatus, formatStep } from '@/lib/utils/workflow';
import { getStatusEventConfig, EVENT_TYPE_CONFIGS, createEventIcon } from '@/lib/constants/workflowInsights';

export interface WorkflowInsightEvent {
    id: string;
    label: string;
    detail?: string;
    icon: React.ReactNode;
    timestamp: Date;
}

interface UseWorkflowInsightsProps {
    status: WorkflowState['status'];
    currentStep?: string | null;
    moodAnalysis: WorkflowState['moodAnalysis'];
    recommendations: WorkflowState['recommendations'];
    anchorTracks?: WorkflowState['anchorTracks'];
    metadata?: WorkflowState['metadata'];
    error: string | null;
}

/**
 * Custom hook to track and manage workflow insight events
 */
export function useWorkflowInsights({
    status,
    currentStep,
    moodAnalysis,
    recommendations,
    anchorTracks,
    metadata,
    error,
}: UseWorkflowInsightsProps) {
    const [events, setEvents] = useState<WorkflowInsightEvent[]>([]);

    // Track previous values to detect changes
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

    const timeFormatter = useMemo(
        () => new Intl.DateTimeFormat(undefined, {
            hour: 'numeric',
            minute: '2-digit',
        }),
        []
    );

    const resetHistory = useCallback(() => {
        setEvents([]);
        prevStatusRef.current = null;
        prevRecoCountRef.current = 0;
        prevAnchorCountRef.current = 0;
        prevIterationRef.current = undefined;
        moodLoggedRef.current = false;
        eventIdRef.current = 0;
    }, []);

    // Reset when workflow ends or errors
    useEffect(() => {
        if (!status || isTerminalStatus(status) || error) {
            resetHistory();
        }
    }, [status, error, resetHistory]);

    useEffect(() => {
        if (!status || isTerminalStatus(status) || error) {
            return;
        }

        const entries: WorkflowInsightEvent[] = [];

        const pushEvent = (label: string, detail: string | undefined, icon: React.ReactNode) => {
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
            const config = getStatusEventConfig(status);
            const enrichedDetail = formatStep(currentStep) || config.detail;
            pushEvent(config.label, enrichedDetail, createEventIcon(config));
        }

        // Mood analysis ready
        if (!moodLoggedRef.current && primaryEmotion) {
            pushEvent(
                EVENT_TYPE_CONFIGS.moodDecoded.label,
                `Primary emotion: ${primaryEmotion}`,
                createEventIcon(EVENT_TYPE_CONFIGS.moodDecoded)
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
                EVENT_TYPE_CONFIGS.anchorsLocked.label,
                detail,
                createEventIcon(EVENT_TYPE_CONFIGS.anchorsLocked)
            );
        }

        // Recommendations arriving
        if (recommendationCount > prevRecoCountRef.current) {
            const diff = recommendationCount - prevRecoCountRef.current;
            pushEvent(
                `Added ${diff} track${diff === 1 ? '' : 's'}`,
                `Now at ${recommendationCount} curated pick${recommendationCount === 1 ? '' : 's'}`,
                createEventIcon(EVENT_TYPE_CONFIGS.tracksAdded)
            );
        }

        // Optimization iterations
        if (iterationValue && iterationValue !== prevIterationRef.current) {
            pushEvent(
                `${EVENT_TYPE_CONFIGS.optimizationPass.label} ${iterationValue}`,
                'Fine-tuning for cohesion and flow',
                createEventIcon(EVENT_TYPE_CONFIGS.optimizationPass)
            );
        }

        if (entries.length > 0) {
            setEvents(prev => {
                return [...entries, ...prev];
            });
        }

        // Update refs
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
        resetHistory,
    ]);

    return {
        events,
        timeFormatter,
        hasEvents: events.length > 0,
    };
}

