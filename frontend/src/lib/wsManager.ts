// Optimized WebSocket manager using reconnecting-websocket
// Provides automatic reconnection, better error handling, and simplified logic

import ReconnectingWebSocket, { type CloseEvent } from 'reconnecting-websocket';
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
    socket: ReconnectingWebSocket;
    callbacks: WSCallbacks;
    pingInterval?: NodeJS.Timeout;
    isReconnecting: boolean;
    manuallyClosed: boolean;
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
    startStreaming(sessionId: string, callbacks: WSCallbacks): void {
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
     * Establish WebSocket connection using reconnecting-websocket
     */
    private connect(sessionId: string, callbacks: WSCallbacks): void {
        const protocol = config.api.baseUrl.startsWith('https') ? 'wss' : 'ws';
        const wsUrl = config.api.baseUrl.replace(/^https?/, protocol);
        const url = `${wsUrl}/api/agents/recommendations/${sessionId}/ws`;

        logger.info('Establishing WebSocket connection', {
            component: 'WSManager',
            sessionId,
            url
        });

        const socket = new ReconnectingWebSocket(url, undefined, {
            startClosed: false,
            minReconnectionDelay: this.baseReconnectDelay,
            maxReconnectionDelay: this.maxReconnectDelay,
            reconnectionDelayGrowFactor: 2,
            connectionTimeout: 5000,
            maxRetries: this.maxReconnectAttempts,
        });

        const connection: WSConnection = {
            socket,
            callbacks,
            isReconnecting: false,
            manuallyClosed: false
        };

        this.connections.set(sessionId, connection);

        socket.addEventListener('open', () => {
            logger.info('WebSocket connection established successfully', {
                component: 'WSManager',
                sessionId,
                readyState: socket.readyState,
                url
            });

            // Start ping interval to keep connection alive
            if (!connection.pingInterval) {
                connection.pingInterval = setInterval(() => {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send('ping');
                    }
                }, this.pingIntervalMs);
            }

            // Notify reconnection callback if this was a reconnection
            if (connection.isReconnecting && callbacks.onReconnect) {
                logger.info('WebSocket reconnected successfully', {
                    component: 'WSManager',
                    sessionId
                });
                callbacks.onReconnect();
            }

            connection.isReconnecting = false;
        });

        socket.addEventListener('message', (event) => {
            try {
                const message = JSON.parse(event.data as string);

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
                        {
                            const error = new Error(message.message || message.error || 'WebSocket error');
                            logger.error('Received error message', error, {
                                component: 'WSManager',
                                sessionId
                            });
                            if (callbacks.onError) {
                                callbacks.onError(error);
                            }
                        }
                        break;

                    case 'ping':
                        socket.send('pong');
                        break;

                    case 'pong':
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
        });

        socket.addEventListener('error', () => {
            // reconnecting-websocket handles reconnection automatically
            logger.error('WebSocket error', new Error('WebSocket error event'), {
                component: 'WSManager',
                sessionId,
                readyState: socket.readyState
            });
        });

        socket.addEventListener('close', (event: CloseEvent) => {
            logger.info('WebSocket connection closed', {
                component: 'WSManager',
                sessionId,
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });

            if (connection.pingInterval) {
                clearInterval(connection.pingInterval);
                connection.pingInterval = undefined;
            }

            if (connection.manuallyClosed) {
                return;
            }

            connection.isReconnecting = true;

            const retryCount = (socket as ReconnectingWebSocket & { retryCount?: number }).retryCount ?? 0;
            if (retryCount >= this.maxReconnectAttempts) {
                logger.error('Max WebSocket reconnection attempts reached', undefined, {
                    component: 'WSManager',
                    sessionId,
                    attempts: retryCount
                });

                if (callbacks.onError) {
                    callbacks.onError(new Error('Failed to reconnect after multiple attempts'));
                }

                this.stopStreaming(sessionId);
            }
        });
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

        connection.manuallyClosed = true;

        if (connection.pingInterval) {
            clearInterval(connection.pingInterval);
        }

        connection.socket.close(1000, 'Client closing connection');
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
