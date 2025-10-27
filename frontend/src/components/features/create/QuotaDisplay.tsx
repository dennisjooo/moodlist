'use client';

import { useEffect, useState, useRef, memo } from 'react';
import { userAPI, QuotaStatus } from '@/lib/api/user';
import { logger } from '@/lib/utils/logger';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface QuotaDisplayProps {
    className?: string;
    onRefresh?: () => void;
    onLoadingChange?: (loading: boolean) => void;
}

function QuotaDisplayComponent({ className = '', onRefresh, onLoadingChange }: QuotaDisplayProps) {
    const [quota, setQuota] = useState<QuotaStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const hasFetchedRef = useRef(false);

    const fetchQuota = async () => {
        try {
            setLoading(true);
            const quotaStatus = await userAPI.getQuotaStatus();
            setQuota(quotaStatus);
            setError(null);
            onRefresh?.();
        } catch (err) {
            logger.error('Failed to fetch quota status', err as Error, {
                component: 'QuotaDisplay',
            });
            setError('Failed to load quota status');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Only fetch once per component lifecycle
        if (!hasFetchedRef.current) {
            hasFetchedRef.current = true;
            fetchQuota();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Notify parent when loading state changes
    useEffect(() => {
        onLoadingChange?.(loading);
    }, [loading, onLoadingChange]);

    if (loading) {
        return (
            <div className={`animate-pulse ${className}`}>
                <div className="h-16 bg-muted/50 rounded-lg" />
            </div>
        );
    }

    if (error || !quota) {
        return null;
    }

    const percentage = (quota.used / quota.limit) * 100;
    const isNearLimit = percentage >= 80;
    const isAtLimit = quota.remaining === 0;

    return (
        <div className={`${className}`}>
            <div
                className={`rounded-lg border p-3 transition-colors ${isAtLimit
                    ? 'border-destructive/50 bg-destructive/5'
                    : isNearLimit
                        ? 'border-warning/50 bg-warning/5'
                        : 'border-border bg-card'
                    }`}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-0.5">
                            {isAtLimit ? (
                                <AlertCircle className="h-3.5 w-3.5 text-destructive" />
                            ) : isNearLimit ? (
                                <Clock className="h-3.5 w-3.5 text-warning" />
                            ) : (
                                <CheckCircle className="h-3.5 w-3.5 text-success" />
                            )}
                            <h3 className="text-xs font-medium">Daily Quota</h3>
                        </div>
                        <p className="text-xs text-muted-foreground">
                            {isAtLimit ? (
                                <>
                                    All done for today! Resets at midnight UTC.
                                </>
                            ) : (
                                <>
                                    You can create <span className="font-semibold text-foreground">{quota.remaining}</span> more playlist
                                    {quota.remaining !== 1 ? 's' : ''} today
                                </>
                            )}
                        </p>
                    </div>
                    <div className="text-right">
                        <div className="text-xl font-bold">
                            {quota.used}
                            <span className="text-xs text-muted-foreground">/{quota.limit}</span>
                        </div>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                        className={`h-full transition-all duration-300 ${isAtLimit
                            ? 'bg-destructive'
                            : isNearLimit
                                ? 'bg-warning'
                                : 'bg-primary'
                            }`}
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                </div>
            </div>
        </div>
    );
}

// Memoize to prevent unnecessary re-renders when parent updates
export const QuotaDisplay = memo(QuotaDisplayComponent);
QuotaDisplay.displayName = 'QuotaDisplay';
