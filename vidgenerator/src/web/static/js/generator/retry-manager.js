/**
 * Retry Manager for API Requests
 * Implements exponential backoff retry logic
 */

class RetryManager {
    constructor(config = {}) {
        this.maxRetries = config.maxRetries || 3;
        this.baseDelay = config.baseDelay || 1000; // 1 second
        this.maxDelay = config.maxDelay || 10000; // 10 seconds
        this.retryableStatuses = config.retryableStatuses || [408, 429, 500, 502, 503, 504];
        this.retryableErrors = config.retryableErrors || ['NetworkError', 'TimeoutError', 'AbortError'];
    }
    
    /**
     * Check if error is retryable
     */
    isRetryable(error, response = null) {
        // Network errors are always retryable
        if (error.name && this.retryableErrors.includes(error.name)) {
            return true;
        }
        
        // Check HTTP status codes
        if (response && this.retryableStatuses.includes(response.status)) {
            return true;
        }
        
        // Check error message for network-related keywords
        const errorMessage = error.message?.toLowerCase() || '';
        const networkKeywords = ['network', 'timeout', 'connection', 'fetch', 'failed'];
        if (networkKeywords.some(keyword => errorMessage.includes(keyword))) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Calculate delay for retry (exponential backoff)
     */
    calculateDelay(attempt) {
        // Exponential backoff: baseDelay * 2^attempt
        const delay = Math.min(
            this.baseDelay * Math.pow(2, attempt),
            this.maxDelay
        );
        
        // Add jitter (random 0-30% of delay) to prevent thundering herd
        const jitter = delay * 0.3 * Math.random();
        return Math.floor(delay + jitter);
    }
    
    /**
     * Retry a function with exponential backoff
     */
    async retry(fn, context = {}) {
        let lastError = null;
        let lastResponse = null;
        
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                const result = await fn();
                
                // If we have a response, check status
                if (result && result.response) {
                    lastResponse = result.response;
                    
                    // If response is OK, return it
                    if (result.response.ok) {
                        return result;
                    }
                    
                    // If not retryable, throw error
                    if (!this.isRetryable(null, result.response)) {
                        throw new Error(`HTTP ${result.response.status}: ${result.response.statusText}`);
                    }
                } else {
                    // No response object, assume success
                    return result;
                }
                
            } catch (error) {
                lastError = error;
                
                // Check if error is retryable
                if (!this.isRetryable(error, lastResponse)) {
                    throw error; // Not retryable, throw immediately
                }
                
                // If this was the last attempt, throw the error
                if (attempt === this.maxRetries) {
                    throw error;
                }
                
                // Calculate delay and wait
                const delay = this.calculateDelay(attempt);
                
                // Notify about retry if callback provided
                if (context.onRetry) {
                    context.onRetry(attempt + 1, this.maxRetries, delay, error);
                }
                
                // Wait before retrying
                await this.sleep(delay);
            }
        }
        
        // Should never reach here, but just in case
        throw lastError || new Error('Retry failed');
    }
    
    /**
     * Sleep utility
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Wrap a fetch call with retry logic
     */
    async fetchWithRetry(url, options = {}, context = {}) {
        return this.retry(async () => {
            const response = await fetch(url, options);
            return { response, data: null };
        }, context);
    }
    
    /**
     * Wrap a fetch + json call with retry logic
     */
    async fetchJsonWithRetry(url, options = {}, context = {}) {
        return this.retry(async () => {
            const response = await fetch(url, options);
            
            // Check content type
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(`API returned HTML instead of JSON (${response.status})`);
                }
            }
            
            const data = await response.json();
            return { response, data };
        }, context);
    }
}

// Global instance
const retryManager = new RetryManager({
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000
});

// Make available globally
if (typeof window !== 'undefined') {
    window.retryManager = retryManager;
    window.RetryManager = RetryManager;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RetryManager;
}

