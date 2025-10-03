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
  private consecutiveSuccesses: Map<string, number> = new Map();
  private lastStatusChange: Map<string, number> = new Map();

  private defaultConfig: PollingConfig = {
    interval: 3000,      // 3 seconds base interval (reduced from 2s)
    maxBackoff: 60000,   // 60 seconds max backoff (increased from 30s)
    maxRetries: 5,       // 5 retry attempts (increased from 3)
  };

  startPolling(
    sessionId: string,
    pollFn: () => Promise<any>,
    callbacks: PollingCallbacks,
    config: Partial<PollingConfig> = {}
  ) {
    // Stop any existing polling for this session first
    if (this.intervals.has(sessionId)) {
      console.log('Polling already active for session:', sessionId, '- stopping old one');
      this.stopPolling(sessionId);
    }

    const mergedConfig = { ...this.defaultConfig, ...config };
    const poll = async () => {
      try {
        const result = await pollFn();

        // Reset backoff and retry count on success
        this.backoffMs.delete(sessionId);
        this.retryCount.delete(sessionId);

        // Track consecutive successes for adaptive polling
        const currentSuccesses = this.consecutiveSuccesses.get(sessionId) || 0;
        this.consecutiveSuccesses.set(sessionId, currentSuccesses + 1);

        // Track status changes for adaptive polling
        const lastStatus = this.lastStatusChange.get(sessionId);
        if (lastStatus !== result.status) {
          this.lastStatusChange.set(sessionId, result.status);
          this.consecutiveSuccesses.set(sessionId, 0); // Reset on status change
        }

        // Notify callbacks
        callbacks.onStatus(result);

        // Determine next polling interval with adaptive logic
        const baseInterval = this.getNextInterval(result.status, result.awaiting_input);
        const adaptiveInterval = this.getAdaptiveInterval(sessionId, baseInterval, result.status);

        if (this.shouldStopPolling(result.status)) {
          this.stopPolling(sessionId);
          if (callbacks.onComplete) {
            callbacks.onComplete();
          }
        } else if (result.awaiting_input && callbacks.onAwaitingInput) {
          callbacks.onAwaitingInput();
          // Poll less frequently when waiting for user input
          this.schedulePoll(sessionId, adaptiveInterval, poll, mergedConfig);
        } else {
          // Normal polling during active processing with adaptive timing
          this.schedulePoll(sessionId, adaptiveInterval, poll, mergedConfig);
        }

      } catch (error) {
        console.error('Polling error for session:', sessionId, error);

        // Reset consecutive successes on error
        this.consecutiveSuccesses.delete(sessionId);

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
      return 8000; // Poll every 8 seconds when waiting for user input (increased from 5s)
    }

    switch (status) {
      case 'analyzing_mood':
        return 4000; // Poll every 4 seconds for mood analysis (increased from 2s)
      case 'gathering_seeds':
        return 3500; // Poll every 3.5 seconds for seed gathering (increased from 2s)
      case 'generating_recommendations':
        return 3000; // Poll every 3 seconds for recommendation generation (increased from 2s)
      case 'processing_edits':
        return 2500; // Poll every 2.5 seconds for edit processing (increased from 2s)
      case 'creating_playlist':
        return 2000; // Poll every 2 seconds for playlist creation (same as before)
      case 'pending':
        return 5000; // Poll every 5 seconds for pending (increased from 3s)
      case 'evaluating_quality':
      case 'optimizing_recommendations':
        return 3500; // Poll every 3.5 seconds for quality evaluation/optimization
      case 'completed':
      case 'failed':
        return 0; // Stop polling
      default:
        return 4000; // Default to 4 seconds (increased from 2s)
    }
  }

  private shouldStopPolling(status: string): boolean {
    return status === 'completed' || status === 'failed';
  }

  private getAdaptiveInterval(sessionId: string, baseInterval: number, status: string): number {
    const consecutiveSuccesses = this.consecutiveSuccesses.get(sessionId) || 0;

    // If we have many consecutive successes, we can poll less frequently
    // This reduces server load when workflow is progressing smoothly
    if (consecutiveSuccesses > 10) {
      // After 10+ successes, increase interval by 50%
      return Math.floor(baseInterval * 1.5);
    } else if (consecutiveSuccesses > 5) {
      // After 5+ successes, increase interval by 25%
      return Math.floor(baseInterval * 1.25);
    }

    // For critical states, keep base interval
    if (status === 'creating_playlist' || status === 'processing_edits') {
      return baseInterval;
    }

    return baseInterval;
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
    this.consecutiveSuccesses.delete(sessionId);
    this.lastStatusChange.delete(sessionId);
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