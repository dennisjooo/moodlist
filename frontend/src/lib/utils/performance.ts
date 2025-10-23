/**
 * Performance monitoring utilities for tracking component metrics
 */
import { logger } from '@/lib/utils/logger';

export interface PerformanceMetric {
    component: string;
    action: string;
    duration: number;
    timestamp: number;
    metadata?: Record<string, unknown>;
}

/**
 * Track a performance metric
 */
export function trackPerformanceMetric(
    component: string,
    action: string,
    duration: number,
    metadata?: Record<string, unknown>
): void {
    const metric: PerformanceMetric = {
        component,
        action,
        duration,
        timestamp: Date.now(),
        metadata,
    };

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
        logger.debug(`[Performance] ${component}.${action}: ${duration.toFixed(2)}ms`, metadata);
    }

    // In production, you could send to analytics service
    // Example: sendToAnalytics('performance_metric', metric);

    // Store in localStorage for debugging (last 100 metrics)
    try {
        const stored = localStorage.getItem('performance_metrics');
        const metrics: PerformanceMetric[] = stored ? JSON.parse(stored) : [];
        metrics.push(metric);

        // Keep only last 100 metrics
        if (metrics.length > 100) {
            metrics.shift();
        }

        localStorage.setItem('performance_metrics', JSON.stringify(metrics));
    } catch {
        // Ignore localStorage errors
    }
}

/**
 * Create a performance timer
 */
export function createPerformanceTimer(component: string, action: string) {
    const startTime = performance.now();

    return {
        end: (metadata?: Record<string, unknown>) => {
            const duration = performance.now() - startTime;
            trackPerformanceMetric(component, action, duration, metadata);
            return duration;
        },
    };
}

/**
 * React hook for measuring component mount time
 */
export function useComponentPerformance(componentName: string) {
    const mountTime = performance.now();

    const trackAction = (action: string, metadata?: Record<string, unknown>) => {
        const duration = performance.now() - mountTime;
        trackPerformanceMetric(componentName, action, duration, metadata);
    };

    return { trackAction };
}

/**
 * Get stored performance metrics (for debugging)
 */
export function getPerformanceMetrics(): PerformanceMetric[] {
    try {
        const stored = localStorage.getItem('performance_metrics');
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

/**
 * Clear stored performance metrics
 */
export function clearPerformanceMetrics(): void {
    try {
        localStorage.removeItem('performance_metrics');
    } catch {
        // Ignore errors
    }
}
