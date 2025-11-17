'use client';

import { isTerminalStatus } from '@/lib/utils/workflow';
import { useEffect, useMemo, useRef, useState } from 'react';
import { resolveStageForStatus } from './workflowStageConfig';

interface PerceivedProgressOptions {
    /**
     * Minimum progress to show when workflow just started (helps avoid 0% perception)
     */
    baseProgress?: number;
    /**
     * How much of each stage's weight we can consume while the stage is active.
     * Keeps some headroom so we never hit 100% too early.
     */
    stageConsumptionFactor?: number;
}

interface PerceivedProgressState {
    /**
     * Current progress percentage (0-100)
     */
    percent: number;
    /**
     * Progress as decimal fraction (0-1)
     */
    progress: number;
    /**
     * Index of the active stage in the workflow
     */
    stageIndex: number;
    /**
     * Display label for the current stage
     */
    stageLabel: string;
}

const DEFAULT_OPTIONS: Required<PerceivedProgressOptions> = {
    baseProgress: 0.03,
    stageConsumptionFactor: 0.88,
};

/**
 * Smoothly animates progress across workflow stages to give users a sense of momentum.
 */
export function usePerceivedProgress(status: string | null, options: PerceivedProgressOptions = {}): PerceivedProgressState {
    const { baseProgress, stageConsumptionFactor } = { ...DEFAULT_OPTIONS, ...options };
    const stageInfo = useMemo(() => resolveStageForStatus(status), [status]);

    const [progress, setProgress] = useState(() => Math.max(baseProgress, stageInfo.cumulativeWeight));
    const animationRef = useRef<number | undefined>(undefined);

    useEffect(() => {
        // Cancel any pending frames when dependencies change
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current);
        }

        const { cumulativeWeight, weight, index } = stageInfo;
        const stageMaxProgress = cumulativeWeight + weight * stageConsumptionFactor;

        const targetProgress = isTerminalStatus(status)
            ? 1
            : Math.max(baseProgress, Math.min(stageMaxProgress, 0.98));

        const animate = () => {
            setProgress(prev => {
                if (prev >= targetProgress) {
                    return Math.max(prev, targetProgress);
                }

                const delta = targetProgress - prev;
                // Larger steps for earlier stages, smaller for later for a smoother feel
                const easingFactor = 0.12 + index * 0.02;
                const nextValue = prev + delta * Math.min(0.25, easingFactor);
                return Math.min(nextValue, targetProgress);
            });

            animationRef.current = requestAnimationFrame(animate);
        };

        animationRef.current = requestAnimationFrame(animate);

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [stageInfo, baseProgress, stageConsumptionFactor, status]);

    const stageLabel = stageInfo.stage.label;
    const stageIndex = stageInfo.index;

    return {
        progress,
        percent: Math.round(progress * 100),
        stageIndex,
        stageLabel,
    };
}
