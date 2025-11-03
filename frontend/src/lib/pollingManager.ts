// Polling manager with exponential backoff for workflow status updates
// Based on the polling strategy from FRONTEND_INTEGRATION_GUIDE.md
import { config } from '@/lib/config';
import { logger } from '@/lib/utils/logger';
import { WorkflowStatus } from './workflowApi';
import { isTerminalStatus } from '@/lib/utils/workflow';

export interface PollingConfig {
  interval: number;        // Base polling interval in ms
  maxBackoff: number;      // Maximum backoff delay in ms
  maxRetries: number;      // Maximum retry attempts
}

export interface PollingCallbacks {
  onStatus: (status: WorkflowStatus) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
  onAwaitingInput?: () => void;
}

export class PollingManager {
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private backoffMs: Map<string, number> = new Map();
  private retryCount: Map<string, number> = new Map();

  private defaultConfig: PollingConfig = {
    interval: config.polling.baseInterval,
    maxBackoff: config.polling.maxBackoff,
    maxRetries: config.polling.maxRetries,
  };

  startPolling(
    sessionId: string,
    pollFn: () => Promise<WorkflowStatus>,
    callbacks: PollingCallbacks,
    config: Partial<PollingConfig> = {}
  ) {
    // Stop any existing polling for this session first
    if (this.intervals.has(sessionId)) {
      logger.debug('Polling already active - restarting', { component: 'PollingManager', sessionId });
      this.stopPolling(sessionId);
    }

    const mergedConfig = { ...this.defaultConfig, ...config };
    const poll = async () => {
      try {
        const result = await pollFn();

        // Reset backoff and retry count on success
        this.backoffMs.delete(sessionId);
        this.retryCount.delete(sessionId);

        // Notify callbacks
        callbacks.onStatus(result);

        // Determine next polling interval based on status
        const nextInterval = this.getNextInterval(result.status, result.awaiting_input);

        if (this.shouldStopPolling(result.status)) {
          this.stopPolling(sessionId);
          if (callbacks.onComplete) {
            callbacks.onComplete();
          }
        } else if (result.awaiting_input && callbacks.onAwaitingInput) {
          callbacks.onAwaitingInput();
          // Poll less frequently when waiting for user input
          this.schedulePoll(sessionId, nextInterval, poll);
        } else {
          // Normal polling during active processing
          this.schedulePoll(sessionId, nextInterval, poll);
        }

      } catch (error) {
        logger.error('Polling error', error, { component: 'PollingManager', sessionId });

        const currentRetryCount = this.retryCount.get(sessionId) || 0;
        const currentBackoff = this.backoffMs.get(sessionId) || mergedConfig.interval;

        if (currentRetryCount >= mergedConfig.maxRetries) {
          this.stopPolling(sessionId);
          if (callbacks.onError) {
            callbacks.onError(error instanceof Error ? error : new Error('Polling failed'));
          }
        } else {
          // Exponential backoff on error
          const nextBackoff = Math.min(currentBackoff * 2, mergedConfig.maxBackoff);
          this.backoffMs.set(sessionId, nextBackoff);
          this.retryCount.set(sessionId, currentRetryCount + 1);

          this.schedulePoll(sessionId, nextBackoff, poll);

          if (callbacks.onError) {
            callbacks.onError(error instanceof Error ? error : new Error('Polling failed'));
          }
        }
      }
    };

    // Start polling immediately
    poll();
  }

  private getNextInterval(status: string, awaitingInput: boolean): number {
    if (awaitingInput) {
      return config.polling.awaitingInputInterval; // Poll less frequently when waiting for user input
    }

    switch (status) {
      case 'analyzing_mood':
      case 'gathering_seeds':
      case 'generating_recommendations':
      case 'processing_edits':
      case 'creating_playlist':
        return config.polling.baseInterval; // Active processing interval
      case 'pending':
        return config.polling.pendingInterval; // Pending interval
      case 'completed':
      case 'failed':
        return 0; // Stop polling
      default:
        return config.polling.baseInterval; // Default interval
    }
  }

  private shouldStopPolling(status: string): boolean {
    return isTerminalStatus(status);
  }

  private schedulePoll(
    sessionId: string,
    delayMs: number,
    pollFn: () => Promise<void>
  ) {
    this.stopPolling(sessionId);

    if (delayMs > 0) {
      const interval = setTimeout(() => {
        this.intervals.delete(sessionId);
        pollFn();
      }, delayMs);

      this.intervals.set(sessionId, interval);
    }
  }

  stopPolling(sessionId: string) {
    const interval = this.intervals.get(sessionId);
    if (interval) {
      clearTimeout(interval);
      this.intervals.delete(sessionId);
    }
    this.backoffMs.delete(sessionId);
    this.retryCount.delete(sessionId);
  }

  // Stop all active polling sessions
  stopAllPolling() {
    for (const sessionId of this.intervals.keys()) {
      this.stopPolling(sessionId);
    }
  }
}

// Singleton instance
export const pollingManager = new PollingManager();