/**
 * Polling Utility with Exponential Backoff
 * Provides intelligent polling with exponential backoff for failed requests
 */
class PollingUtility {
    constructor(options = {}) {
        this.baseInterval = options.baseInterval || 30000; // 30 seconds default
        this.maxInterval = options.maxInterval || 300000; // 5 minutes max
        this.backoffMultiplier = options.backoffMultiplier || 2;
        this.maxRetries = options.maxRetries || 5;
        this.currentInterval = this.baseInterval;
        this.retryCount = 0;
        this.intervalId = null;
        this.isRunning = false;
        this.onSuccess = options.onSuccess || (() => {});
        this.onError = options.onError || (() => {});
        this.pollFunction = options.pollFunction || null;
    }

    /**
     * Start polling with exponential backoff
     */
    start() {
        if (this.isRunning) {
            return;
        }
        
        this.isRunning = true;
        this.currentInterval = this.baseInterval;
        this.retryCount = 0;
        this._scheduleNext();
    }

    /**
     * Stop polling
     */
    stop() {
        this.isRunning = false;
        if (this.intervalId) {
            clearTimeout(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Reset to base interval (call after successful request)
     */
    reset() {
        this.currentInterval = this.baseInterval;
        this.retryCount = 0;
    }

    /**
     * Schedule next poll
     */
    _scheduleNext() {
        if (!this.isRunning) {
            return;
        }

        this.intervalId = setTimeout(async () => {
            if (!this.isRunning) {
                return;
            }

            try {
                if (this.pollFunction) {
                    const result = await this.pollFunction();
                    
                    // Check if result indicates success
                    if (result && (result.success !== false)) {
                        // Success - reset interval
                        this.reset();
                        this.onSuccess(result);
                    } else {
                        // Failure - increase interval
                        this._handleFailure();
                        this.onError(result);
                    }
                }
            } catch (error) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(error instanceof Error ? error : new Error(String(error)), { source: 'polling-utility.js', context: 'catch' }); }
                this._handleFailure();
                this.onError({ success: false, error: error.message });
            }

            // Schedule next poll
            this._scheduleNext();
        }, this.currentInterval);
    }

    /**
     * Handle failure with exponential backoff
     */
    _handleFailure() {
        this.retryCount++;
        
        // Increase interval exponentially
        this.currentInterval = Math.min(
            this.currentInterval * this.backoffMultiplier,
            this.maxInterval
        );

        // If max retries reached, stop or reset
        if (this.retryCount >= this.maxRetries) {
            console.warn('Polling: Max retries reached, resetting interval');
            this.reset();
        }
    }

    /**
     * Create a polling instance for a specific function
     */
    static create(pollFunction, options = {}) {
        return new PollingUtility({
            ...options,
            pollFunction
        });
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.PollingUtility = PollingUtility;
}
