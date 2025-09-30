// Polling manager with exponential backoff for workflow status updates
// Based on the polling strategy from FRONTEND_INTEGRATION_GUIDE.md

export interface PollingConfig {
  interval: number;        // Base polling interval in ms
  maxBackoff: number;      // Maximum backoff delay in ms
  maxRetries: number;      // Maximum retry attempts
}

export interface PollingCallbacks {
  onStatus: (status: any) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
  onAwaitingInput?: () => void;
}

export class PollingManager {
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private backoffMs: Map<string, number> = new Map();
  private retryCount: Map<string, number> = new Map();

  private defaultConfig: PollingConfig = {
    interval: 2000,      // 2 seconds base interval
    maxBackoff: 30000,   // 30 seconds max backoff
    maxRetries: 3,       // 3 retry attempts
  };

  startPolling(
    sessionId: string,
    pollFn: () => Promise<any>,
    callbacks: PollingCallbacks,
    config: Partial<PollingConfig> = {}
  ) {
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
          this.schedulePoll(sessionId, nextInterval, poll, mergedConfig);
        } else {
          // Normal polling during active processing
          this.schedulePoll(sessionId, nextInterval, poll, mergedConfig);
        }

      } catch (error) {
        console.error('Polling error:', error);

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

          this.schedulePoll(sessionId, nextBackoff, poll, mergedConfig);

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
      return 5000; // Poll every 5 seconds when waiting for user input
    }

    switch (status) {
      case 'analyzing_mood':
      case 'gathering_seeds':
      case 'generating_recommendations':
      case 'processing_edits':
      case 'creating_playlist':
        return 2000; // Poll every 2 seconds during active processing
      case 'pending':
        return 3000; // Poll every 3 seconds for pending
      case 'completed':
      case 'failed':
        return 0; // Stop polling
      default:
        return 2000; // Default to 2 seconds
    }
  }

  private shouldStopPolling(status: string): boolean {
    return status === 'completed' || status === 'failed';
  }

  private schedulePoll(
    sessionId: string,
    delayMs: number,
    pollFn: () => Promise<void>,
    config: PollingConfig
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