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
                className={`rounded-2xl border border-border/40 bg-background/80 p-4 shadow-[0_18px_40px_-25px_rgba(15,23,42,0.4)] backdrop-blur-xl transition-colors animate-in fade-in duration-300 ${isAtLimit
                    ? 'ring-1 ring-inset ring-destructive/40'
                    : isNearLimit
                        ? 'ring-1 ring-inset ring-warning/40'
                        : ''
                    }`}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                        <div className="mb-1 flex items-center gap-2">
                            {isAtLimit ? (
                                <AlertCircle className="h-3.5 w-3.5 text-destructive" />
                            ) : isNearLimit ? (
                                <Clock className="h-3.5 w-3.5 text-warning" />
                            ) : (
                                <CheckCircle className="h-3.5 w-3.5 text-success" />
                            )}
                            <h3 className="text-xs font-medium tracking-[0.28em] text-muted-foreground/80">Daily quota</h3>
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
                        <div className="text-xl font-semibold text-foreground">
                            {quota.used}
                            <span className="text-xs text-muted-foreground">/{quota.limit}</span>
                        </div>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted/60">
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
