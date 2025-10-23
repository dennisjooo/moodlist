// SSE manager for real-time workflow status updates
// Replaces polling with efficient Server-Sent Events

import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import { WorkflowStatus } from './api/workflow';

export interface SSECallbacks {
    onStatus: (status: WorkflowStatus) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
    onReconnect?: () => void;
}

interface SSEConnection {
    eventSource: EventSource;
    callbacks: SSECallbacks;
    reconnectAttempts: number;
    reconnectTimer?: NodeJS.Timeout;
}

export class SSEManager {
    private connections: Map<string, SSEConnection> = new Map();
    private maxReconnectAttempts = 5;
    private baseReconnectDelay = 1000; // 1 second
    private maxReconnectDelay = 30000; // 30 seconds

    /**
     * Check if SSE is supported by the browser
     */
    isSupported(): boolean {
        return typeof EventSource !== 'undefined';
    }

    /**
     * Start SSE connection for a workflow session
     */
    startStreaming(
        sessionId: string,
        callbacks: SSECallbacks
    ): void {
        // Stop any existing connection first
        if (this.connections.has(sessionId)) {
            logger.debug('SSE connection already exists - closing and restarting', {
                component: 'SSEManager',
                sessionId
            });
            this.stopStreaming(sessionId);
        }

        this.connect(sessionId, callbacks);
    }

    /**
     * Establish SSE connection
     */
    private connect(sessionId: string, callbacks: SSECallbacks): void {
        const url = `${config.api.baseUrl}/api/agents/recommendations/${sessionId}/stream`;

        logger.info('Establishing SSE connection', {
            component: 'SSEManager',
            sessionId,
            url
        });

        try {
            const eventSource = new EventSource(url, {
                withCredentials: true
            });

            const connection: SSEConnection = {
                eventSource,
                callbacks,
                reconnectAttempts: 0
            };

            this.connections.set(sessionId, connection);

            // Handle generic message events (for keep-alive and debugging)
            eventSource.onmessage = (event: MessageEvent) => {
                // Keep-alive messages or other generic messages
                if (event.data && event.data.startsWith(':')) {
                    logger.debug('Received keep-alive message', {
                        component: 'SSEManager',
                        sessionId
                    });
                    return;
                }
                // Log unexpected message format
                logger.debug('Received generic SSE message', {
                    component: 'SSEManager',
                    sessionId,
                    data: event.data
                });
            };

            // Handle status updates
            eventSource.addEventListener('status', (event: MessageEvent) => {
                try {
                    const status = JSON.parse(event.data) as WorkflowStatus;
                    logger.info('Received status update via SSE', {
                        component: 'SSEManager',
                        sessionId,
                        status: status.status,
                        currentStep: status.current_step
                    });
                    // Immediately invoke callback to ensure real-time update
                    callbacks.onStatus(status);
                } catch (error) {
                    logger.error('Failed to parse status event', error, {
                        component: 'SSEManager',
                        sessionId,
                        eventData: event.data
                    });
                }
            });

            // Handle completion
            eventSource.addEventListener('complete', (event: MessageEvent) => {
                try {
                    const status = JSON.parse(event.data) as WorkflowStatus;
                    logger.info('Workflow completed', {
                        component: 'SSEManager',
                        sessionId,
                        status: status.status
                    });
                    callbacks.onStatus(status);
                    if (callbacks.onComplete) {
                        callbacks.onComplete();
                    }
                    this.stopStreaming(sessionId);
                } catch (error) {
                    logger.error('Failed to parse complete event', error, {
                        component: 'SSEManager',
                        sessionId
                    });
                }
            });

            // Handle errors
            eventSource.addEventListener('error', (event: MessageEvent) => {
                try {
                    const errorData = JSON.parse(event.data);
                    const error = new Error(errorData.message || 'SSE error event');
                    logger.error('Received error event', error, {
                        component: 'SSEManager',
                        sessionId
                    });
                    if (callbacks.onError) {
                        callbacks.onError(error);
                    }
                } catch (parseError) {
                    // Event might not have data, ignore
                    logger.debug('Error event without parseable data', {
                        component: 'SSEManager',
                        sessionId
                    });
                }
            });

            // Handle connection errors and reconnection
            eventSource.onerror = (event) => {
                logger.warn('SSE connection error', {
                    component: 'SSEManager',
                    sessionId,
                    readyState: eventSource.readyState
                });

                // EventSource.CLOSED = 2
                if (eventSource.readyState === 2) {
                    logger.info('SSE connection closed', {
                        component: 'SSEManager',
                        sessionId
                    });
                    this.handleReconnect(sessionId);
                }
            };

            // Handle successful connection
            eventSource.onopen = () => {
                logger.info('SSE connection established successfully', {
                    component: 'SSEManager',
                    sessionId,
                    readyState: eventSource.readyState,
                    url
                });
                // Reset reconnect attempts on successful connection
                const wasReconnecting = connection.reconnectAttempts > 0;
                connection.reconnectAttempts = 0;

                // Notify reconnection callback if this was a reconnection
                if (wasReconnecting && callbacks.onReconnect) {
                    logger.info('SSE reconnected successfully', {
                        component: 'SSEManager',
                        sessionId
                    });
                    callbacks.onReconnect();
                }
            };

        } catch (error) {
            logger.error('Failed to create SSE connection', error, {
                component: 'SSEManager',
                sessionId
            });
            if (callbacks.onError) {
                callbacks.onError(error instanceof Error ? error : new Error('Failed to create SSE connection'));
            }
        }
    }

    /**
     * Handle reconnection with exponential backoff
     */
    private handleReconnect(sessionId: string): void {
        const connection = this.connections.get(sessionId);
        if (!connection) {
            return;
        }

        connection.reconnectAttempts++;

        if (connection.reconnectAttempts > this.maxReconnectAttempts) {
            logger.error('Max reconnection attempts reached', undefined, {
                component: 'SSEManager',
                sessionId,
                attempts: connection.reconnectAttempts
            });

            if (connection.callbacks.onError) {
                connection.callbacks.onError(new Error('Failed to reconnect after multiple attempts'));
            }

            this.stopStreaming(sessionId);
            return;
        }

        // Calculate exponential backoff delay
        const delay = Math.min(
            this.baseReconnectDelay * Math.pow(2, connection.reconnectAttempts - 1),
            this.maxReconnectDelay
        );

        logger.info('Scheduling SSE reconnection', {
            component: 'SSEManager',
            sessionId,
            attempt: connection.reconnectAttempts,
            delayMs: delay
        });

        // Clean up old connection
        connection.eventSource.close();

        // Schedule reconnection
        connection.reconnectTimer = setTimeout(() => {
            logger.debug('Attempting SSE reconnection', {
                component: 'SSEManager',
                sessionId,
                attempt: connection.reconnectAttempts
            });
            this.connect(sessionId, connection.callbacks);
        }, delay);
    }

    /**
     * Stop SSE connection for a session
     */
    stopStreaming(sessionId: string): void {
        const connection = this.connections.get(sessionId);
        if (!connection) {
            return;
        }

        logger.info('Stopping SSE connection', {
            component: 'SSEManager',
            sessionId
        });

        // Clear reconnect timer if exists
        if (connection.reconnectTimer) {
            clearTimeout(connection.reconnectTimer);
        }

        // Close EventSource
        connection.eventSource.close();

        // Remove from connections map
        this.connections.delete(sessionId);
    }

    /**
     * Stop all active SSE connections
     */
    stopAllStreaming(): void {
        logger.info('Stopping all SSE connections', {
            component: 'SSEManager',
            count: this.connections.size
        });

        for (const sessionId of this.connections.keys()) {
            this.stopStreaming(sessionId);
        }
    }

    /**
     * Get active connection count
     */
    getActiveConnectionCount(): number {
        return this.connections.size;
    }
}

// Singleton instance
export const sseManager = new SSEManager();

