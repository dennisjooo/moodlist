// WebSocket manager for real-time workflow status updates
// Cloudflare-friendly alternative to SSE

import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import { WorkflowStatus } from './api/workflow';

export interface WSCallbacks {
    onStatus: (status: WorkflowStatus) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
    onReconnect?: () => void;
}

interface WSConnection {
    socket: WebSocket;
    callbacks: WSCallbacks;
    reconnectAttempts: number;
    reconnectTimer?: NodeJS.Timeout;
    pingInterval?: NodeJS.Timeout;
}

export class WSManager {
    private connections: Map<string, WSConnection> = new Map();
    private maxReconnectAttempts = 5;
    private baseReconnectDelay = 1000; // 1 second
    private maxReconnectDelay = 30000; // 30 seconds
    private pingIntervalMs = 25000; // 25 seconds (keep connection alive)

    /**
     * Check if WebSocket is supported by the browser
     */
    isSupported(): boolean {
        return typeof WebSocket !== 'undefined';
    }

    /**
     * Start WebSocket connection for a workflow session
     */
    startStreaming(
        sessionId: string,
        callbacks: WSCallbacks
    ): void {
        // Stop any existing connection first
        if (this.connections.has(sessionId)) {
            logger.debug('WebSocket connection already exists - closing and restarting', {
                component: 'WSManager',
                sessionId
            });
            this.stopStreaming(sessionId);
        }

        this.connect(sessionId, callbacks);
    }

    /**
     * Establish WebSocket connection
     */
    private connect(sessionId: string, callbacks: WSCallbacks): void {
        // Use wss:// for https, ws:// for http
        const protocol = config.api.baseUrl.startsWith('https') ? 'wss' : 'ws';
        const wsUrl = config.api.baseUrl.replace(/^https?/, protocol);
        const url = `${wsUrl}/api/agents/recommendations/${sessionId}/ws`;

        logger.info('Establishing WebSocket connection', {
            component: 'WSManager',
            sessionId,
            url
        });

        try {
            const socket = new WebSocket(url);

            const connection: WSConnection = {
                socket,
                callbacks,
                reconnectAttempts: 0
            };

            this.connections.set(sessionId, connection);

            // Handle connection open
            socket.onopen = () => {
                logger.info('WebSocket connection established successfully', {
                    component: 'WSManager',
                    sessionId,
                    readyState: socket.readyState,
                    url
                });

                // Reset reconnect attempts on successful connection
                const wasReconnecting = connection.reconnectAttempts > 0;
                connection.reconnectAttempts = 0;

                // Start ping interval to keep connection alive
                connection.pingInterval = setInterval(() => {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send('ping');
                    }
                }, this.pingIntervalMs);

                // Notify reconnection callback if this was a reconnection
                if (wasReconnecting && callbacks.onReconnect) {
                    logger.info('WebSocket reconnected successfully', {
                        component: 'WSManager',
                        sessionId
                    });
                    callbacks.onReconnect();
                }
            };

            // Handle incoming messages
            socket.onmessage = (event: MessageEvent) => {
                try {
                    const message = JSON.parse(event.data);

                    logger.debug('WebSocket message received', {
                        component: 'WSManager',
                        sessionId,
                        type: message.type
                    });

                    switch (message.type) {
                        case 'connected':
                            logger.info('WebSocket connection confirmed', {
                                component: 'WSManager',
                                sessionId
                            });
                            break;

                        case 'status':
                            logger.info('Received status update via WebSocket', {
                                component: 'WSManager',
                                sessionId,
                                status: message.data.status,
                                currentStep: message.data.current_step
                            });
                            callbacks.onStatus(message.data as WorkflowStatus);
                            break;

                        case 'complete':
                            logger.info('Workflow completed', {
                                component: 'WSManager',
                                sessionId,
                                status: message.data.status
                            });
                            callbacks.onStatus(message.data as WorkflowStatus);
                            if (callbacks.onComplete) {
                                callbacks.onComplete();
                            }
                            this.stopStreaming(sessionId);
                            break;

                        case 'error':
                            const error = new Error(message.message || message.error || 'WebSocket error');
                            logger.error('Received error message', error, {
                                component: 'WSManager',
                                sessionId
                            });
                            if (callbacks.onError) {
                                callbacks.onError(error);
                            }
                            break;

                        case 'ping':
                            // Respond to server ping
                            socket.send('pong');
                            break;

                        case 'pong':
                            // Server acknowledged our ping
                            logger.debug('Received pong', {
                                component: 'WSManager',
                                sessionId
                            });
                            break;

                        default:
                            logger.debug('Unknown message type', {
                                component: 'WSManager',
                                sessionId,
                                type: message.type
                            });
                    }
                } catch (error) {
                    logger.error('Failed to parse WebSocket message', error, {
                        component: 'WSManager',
                        sessionId,
                        data: event.data
                    });
                }
            };

            // Handle errors
            socket.onerror = (event) => {
                logger.error('WebSocket error', new Error('WebSocket error event'), {
                    component: 'WSManager',
                    sessionId,
                    readyState: socket.readyState
                });
            };

            // Handle connection close
            socket.onclose = (event) => {
                logger.info('WebSocket connection closed', {
                    component: 'WSManager',
                    sessionId,
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean
                });

                // Clear ping interval
                if (connection.pingInterval) {
                    clearInterval(connection.pingInterval);
                    connection.pingInterval = undefined;
                }

                // Attempt reconnection if not a clean close
                if (!event.wasClean && event.code !== 1000) {
                    this.handleReconnect(sessionId);
                }
            };

        } catch (error) {
            logger.error('Failed to create WebSocket connection', error, {
                component: 'WSManager',
                sessionId
            });
            if (callbacks.onError) {
                callbacks.onError(error instanceof Error ? error : new Error('Failed to create WebSocket connection'));
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
                component: 'WSManager',
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

        logger.info('Scheduling WebSocket reconnection', {
            component: 'WSManager',
            sessionId,
            attempt: connection.reconnectAttempts,
            delayMs: delay
        });

        // Schedule reconnection
        connection.reconnectTimer = setTimeout(() => {
            logger.debug('Attempting WebSocket reconnection', {
                component: 'WSManager',
                sessionId,
                attempt: connection.reconnectAttempts
            });
            this.connect(sessionId, connection.callbacks);
        }, delay);
    }

    /**
     * Stop WebSocket connection for a session
     */
    stopStreaming(sessionId: string): void {
        const connection = this.connections.get(sessionId);
        if (!connection) {
            return;
        }

        logger.info('Stopping WebSocket connection', {
            component: 'WSManager',
            sessionId
        });

        // Clear reconnect timer if exists
        if (connection.reconnectTimer) {
            clearTimeout(connection.reconnectTimer);
        }

        // Clear ping interval
        if (connection.pingInterval) {
            clearInterval(connection.pingInterval);
        }

        // Close WebSocket
        if (connection.socket.readyState === WebSocket.OPEN ||
            connection.socket.readyState === WebSocket.CONNECTING) {
            connection.socket.close(1000, 'Client closing connection');
        }

        // Remove from connections map
        this.connections.delete(sessionId);
    }

    /**
     * Stop all active WebSocket connections
     */
    stopAllStreaming(): void {
        logger.info('Stopping all WebSocket connections', {
            component: 'WSManager',
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
export const wsManager = new WSManager();
