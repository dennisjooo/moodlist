'use client';

import { useEffect, useRef } from 'react';
import { wsManager } from '@/lib/wsManager';
import { sseManager } from '@/lib/sseManager';
import { logger } from '@/lib/utils/logger';
import { isTerminalStatus } from '@/lib/utils/workflow';
import type { WorkflowStatus } from '@/lib/api/workflow';
import {
    useWebSocketStreaming,
    useSSEStreaming,
    usePollingStreaming,
    type StreamingCallbacks,
} from './streaming';

interface SSECallbacks extends StreamingCallbacks { }

interface UseWorkflowSSEOptions {
    enabled?: boolean;
    callbacks?: SSECallbacks;
    useFallback?: boolean; // Whether to fallback to polling if SSE not supported
}

/**
 * Custom hook to manage workflow SSE connection lifecycle
 * Automatically starts/stops SSE streaming based on session ID and enabled flag
 * Falls back to polling if SSE is not supported
 */
export function useWorkflowSSE(
    sessionId: string | null,
    status: WorkflowStatus['status'] | null,
    options: UseWorkflowSSEOptions = {}
) {
    const { enabled = true, callbacks = {}, useFallback = true } = options;
    const callbacksRef = useRef(callbacks);
    const isUsingSSE = useRef(false);
    const currentStatusRef = useRef(status);
    const terminalHandledRef = useRef(false);

    // Keep callbacks ref up to date
    useEffect(() => {
        callbacksRef.current = callbacks;
    }, [callbacks]);

    // Keep current status ref up to date
    useEffect(() => {
        currentStatusRef.current = status;
    }, [status]);

    useEffect(() => {
        // Reset terminal handled flag for new sessions
        terminalHandledRef.current = false;

        // Don't connect if no session or disabled
        if (!sessionId || !enabled) {
            logger.debug('SSE not starting', {
                component: 'useWorkflowSSE',
                sessionId,
                enabled,
                reason: !sessionId ? 'no sessionId' : 'disabled'
            });
            return;
        }

        // Check if workflow is in a terminal state at connection time
        const isTerminalState = isTerminalStatus(currentStatusRef.current);
        if (isTerminalState) {
            logger.debug('Workflow in terminal state, not starting SSE', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });
            return;
        }

        logger.info('SSE hook effect triggered', {
            component: 'useWorkflowSSE',
            sessionId,
            status: currentStatusRef.current,
            enabled
        });

        // Check WebSocket support (preferred for Cloudflare compatibility)
        const wsSupported = wsManager.isSupported();
        const sseSupported = sseManager.isSupported();

        if (!wsSupported && !sseSupported && !useFallback) {
            logger.warn('WebSocket and SSE not supported and fallback disabled', {
                component: 'useWorkflowSSE',
                sessionId
            });
            if (callbacksRef.current.onError) {
                callbacksRef.current.onError(new Error('WebSocket and SSE not supported by browser'));
            }
            return;
        }

        // Prefer WebSocket (Cloudflare-friendly), fallback to SSE, then polling
        let cleanup: (() => void) | undefined;

        if (wsSupported) {
            logger.info('Starting WebSocket streaming', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });

            isUsingSSE.current = true; // Keep name for backward compat
            cleanup = useWebSocketStreaming(sessionId, callbacksRef.current, terminalHandledRef);

        } else if (sseSupported) {
            logger.info('Starting SSE streaming', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });

            isUsingSSE.current = true;
            cleanup = useSSEStreaming(sessionId, callbacksRef.current, terminalHandledRef);

        } else if (useFallback) {
            // Fallback to polling
            logger.info('SSE not supported, falling back to polling', {
                component: 'useWorkflowSSE',
                sessionId,
                status: currentStatusRef.current
            });

            isUsingSSE.current = false;
            cleanup = usePollingStreaming(sessionId, callbacksRef.current, terminalHandledRef);
        }

        return () => {
            // Cleanup on unmount or when dependencies change
            if (cleanup) {
                cleanup();
            }
        };
    }, [sessionId, enabled, useFallback]);
}

