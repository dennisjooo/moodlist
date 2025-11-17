import { Activity, Compass, ListMusic, Music, Sparkles, TrendingUp, type LucideIcon } from 'lucide-react';
import { createElement, type ReactNode } from 'react';

export interface WorkflowEventConfig {
    label: string;
    detail?: string;
    iconComponent: LucideIcon;
    iconClassName: string;
}

/**
 * Helper function to create icon element from config
 */
export function createEventIcon(config: WorkflowEventConfig): ReactNode {
    return createElement(config.iconComponent, { className: config.iconClassName });
}

/**
 * Configuration for workflow status events displayed in insights
 */
export const WORKFLOW_STATUS_EVENTS: Record<string, WorkflowEventConfig> = {
    analyzing_mood: {
        label: 'Analyzing your vibe',
        detail: 'Reading between the lines of your mood prompt',
        iconComponent: Sparkles,
        iconClassName: 'w-3.5 h-3.5 text-purple-500',
    },
    gathering_seeds: {
        label: 'Gathering musical seeds',
        detail: 'Searching through influences and favorite artists',
        iconComponent: Compass,
        iconClassName: 'w-3.5 h-3.5 text-amber-500',
    },
    generating_recommendations: {
        label: 'Spinning up recommendations',
        detail: 'Matching tracks that mirror your vibe',
        iconComponent: Music,
        iconClassName: 'w-3.5 h-3.5 text-primary',
    },
    evaluating_quality: {
        label: 'Evaluating the flow',
        detail: 'Scoring transitions and cohesion',
        iconComponent: TrendingUp,
        iconClassName: 'w-3.5 h-3.5 text-emerald-500',
    },
    optimizing_recommendations: {
        label: 'Polishing the setlist',
        detail: 'Iterating to nudge scores even higher',
        iconComponent: Sparkles,
        iconClassName: 'w-3.5 h-3.5 text-sky-500',
    },
    ordering_playlist: {
        label: 'Sequencing the playlist',
        detail: 'Shaping the energy arc from start to finish',
        iconComponent: ListMusic,
        iconClassName: 'w-3.5 h-3.5 text-rose-500',
    },
    creating_playlist: {
        label: 'Saving to Spotify',
        detail: 'Packaging everything into your playlist',
        iconComponent: Music,
        iconClassName: 'w-3.5 h-3.5 text-primary',
    },
};

/**
 * Default event config for unknown statuses
 */
export const DEFAULT_STATUS_EVENT: WorkflowEventConfig = {
    label: 'In progress',
    detail: 'Keeping the beat moving',
    iconComponent: Activity,
    iconClassName: 'w-3.5 h-3.5 text-primary',
};

/**
 * Get event configuration for a workflow status
 */
export function getStatusEventConfig(status: string): WorkflowEventConfig {
    const normalized = status.toLowerCase();

    for (const [key, config] of Object.entries(WORKFLOW_STATUS_EVENTS)) {
        if (normalized.includes(key)) {
            return config;
        }
    }

    return DEFAULT_STATUS_EVENT;
}

/**
 * Event type configurations
 */
export const EVENT_TYPE_CONFIGS = {
    moodDecoded: {
        label: 'Mood decoded',
        iconComponent: Sparkles,
        iconClassName: 'w-3.5 h-3.5 text-purple-500',
    },
    anchorsLocked: {
        label: 'Anchors locked',
        iconComponent: Compass,
        iconClassName: 'w-3.5 h-3.5 text-amber-500',
    },
    tracksAdded: {
        label: 'Added tracks',
        iconComponent: Music,
        iconClassName: 'w-3.5 h-3.5 text-primary',
    },
    optimizationPass: {
        label: 'Optimization pass',
        iconComponent: TrendingUp,
        iconClassName: 'w-3.5 h-3.5 text-emerald-500',
    },
} as const;

