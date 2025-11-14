// Optimized SSE manager using @microsoft/fetch-event-source
// Provides better reconnection, error handling, and reliability

import { fetchEventSource } from '@microsoft/fetch-event-source';
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
    abortController: AbortController;
    callbacks: SSECallbacks;
    reconnectCount: number;
    isActive: boolean;
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
        return typeof window !== 'undefined' && typeof fetch !== 'undefined' && typeof AbortController !== 'undefined';
    }

    /**
     * Start SSE connection for a workflow session
     */
    startStreaming(sessionId: string, callbacks: SSECallbacks): void {
        // Stop any existing connection first
        if (this.connections.has(sessionId)) {
            logger.debug('SSE connection already exists - closing and restarting', {
                component: 'SSEManager',
                sessionId
            });
            this.stopStreaming(sessionId);
        }

        const abortController = new AbortController();
        const connection: SSEConnection = {
            abortController,
            callbacks,
            reconnectCount: 0,
            isActive: true
        };

        this.connections.set(sessionId, connection);
        this.connect(sessionId, connection);
    }

    /**
     * Establish SSE connection using fetch-event-source
     */
    private async connect(sessionId: string, connection: SSEConnection): Promise<void> {
        const url = `${config.api.baseUrl}/api/agents/recommendations/${sessionId}/stream`;

        logger.info('Establishing SSE connection', {
            component: 'SSEManager',
            sessionId,
            url
        });

        try {
            await fetchEventSource(url, {
                signal: connection.abortController.signal,
                credentials: 'include',
                
                onopen: async (response) => {
                    if (response.ok) {
                        logger.info('SSE connection established successfully', {
                            component: 'SSEManager',
                            sessionId,
                            status: response.status
                        });

                        // Notify reconnection if this was a reconnect
                        if (connection.reconnectCount > 0 && connection.callbacks.onReconnect) {
                            logger.info('SSE reconnected successfully', {
                                component: 'SSEManager',
                                sessionId,
                                reconnectAttempt: connection.reconnectCount
                            });
                            connection.callbacks.onReconnect();
                        }

                        connection.reconnectCount = 0;
                        return;
                    }

                    // Handle error responses
                    const error = new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
                    logger.error('SSE connection error', error, {
                        component: 'SSEManager',
                        sessionId,
                        status: response.status
                    });

                    if (connection.callbacks.onError) {
                        connection.callbacks.onError(error);
                    }

                    throw error;
                },

                onmessage: (event) => {
                    // Handle keep-alive messages
                    if (!event.data || event.data.startsWith(':')) {
                        logger.debug('Received keep-alive message', {
                            component: 'SSEManager',
                            sessionId
                        });
                        return;
                    }

                    // Handle different event types
                    switch (event.event) {
                        case 'status':
                            try {
                                const status = JSON.parse(event.data) as WorkflowStatus;
                                logger.info('Received status update via SSE', {
                                    component: 'SSEManager',
                                    sessionId,
                                    status: status.status,
                                    currentStep: status.current_step
                                });
                                connection.callbacks.onStatus(status);
                            } catch (error) {
                                logger.error('Failed to parse status event', error, {
                                    component: 'SSEManager',
                                    sessionId,
                                    eventData: event.data
                                });
                            }
                            break;

                        case 'complete':
                            try {
                                const status = JSON.parse(event.data) as WorkflowStatus;
                                logger.info('Workflow completed', {
                                    component: 'SSEManager',
                                    sessionId,
                                    status: status.status
                                });
                                connection.callbacks.onStatus(status);
                                if (connection.callbacks.onComplete) {
                                    connection.callbacks.onComplete();
                                }
                                this.stopStreaming(sessionId);
                            } catch (error) {
                                logger.error('Failed to parse complete event', error, {
                                    component: 'SSEManager',
                                    sessionId
                                });
                            }
                            break;

                        case 'error':
                            try {
                                const errorData = JSON.parse(event.data);
                                const error = new Error(errorData.message || 'SSE error event');
                                logger.error('Received error event', error, {
                                    component: 'SSEManager',
                                    sessionId
                                });
                                if (connection.callbacks.onError) {
                                    connection.callbacks.onError(error);
                                }
                            } catch {
                                logger.debug('Error event without parseable data', {
                                    component: 'SSEManager',
                                    sessionId
                                });
                            }
                            break;

                        default:
                            logger.debug('Received generic SSE message', {
                                component: 'SSEManager',
                                sessionId,
                                event: event.event,
                                data: event.data
                            });
                    }
                },

                onerror: (error) => {
                    logger.error('SSE connection error', error, {
                        component: 'SSEManager',
                        sessionId
                    });

                    // Check if we should retry
                    if (!connection.isActive) {
                        logger.debug('Connection stopped by client, not retrying', {
                            component: 'SSEManager',
                            sessionId
                        });
                        return null; // Stop retrying
                    }

                    connection.reconnectCount++;

                    if (connection.reconnectCount > this.maxReconnectAttempts) {
                        logger.error('Max reconnection attempts reached', undefined, {
                            component: 'SSEManager',
                            sessionId,
                            attempts: connection.reconnectCount
                        });

                        if (connection.callbacks.onError) {
                            connection.callbacks.onError(
                                new Error('Failed to reconnect after multiple attempts')
                            );
                        }

                        this.stopStreaming(sessionId);
                        return null; // Stop retrying
                    }

                    const delay = Math.min(
                        this.baseReconnectDelay * Math.pow(2, connection.reconnectCount - 1),
                        this.maxReconnectDelay
                    );

                    logger.info('Will retry SSE connection', {
                        component: 'SSEManager',
                        sessionId,
                        attempt: connection.reconnectCount,
                        delayMs: delay
                    });

                    return delay; // Tell library to retry after delay
                },

                // fetch-event-source will automatically retry with exponential backoff
                openWhenHidden: true, // Keep connection open when tab is hidden
            });
        } catch (error) {
            // Only log if not aborted (client didn't stop it)
            if (!connection.abortController.signal.aborted) {
                logger.error('SSE connection terminated', error, {
                    component: 'SSEManager',
                    sessionId
                });

                if (connection.callbacks.onError && connection.isActive) {
                    connection.callbacks.onError(
                        error instanceof Error ? error : new Error('SSE connection terminated')
                    );
                }
            }

            // Clean up
            this.connections.delete(sessionId);
        }
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

        connection.isActive = false;
        connection.abortController.abort();
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
