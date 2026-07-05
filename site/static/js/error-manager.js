/**
 * Centralized Error Manager
 * Handles all errors, logs them to database, and provides user-friendly error handling
 */
class ErrorManager {
    constructor() {
        // Try /api/errors first, fallback to /api/errors
        this.apiBase = '/api/errors';
        this.apiBaseFallback = '/api/errors';
        this.userId = null;
        this.sessionId = this.generateSessionId();
        this.errorQueue = [];
        this.isOnline = navigator.onLine;
        this.maxQueueSize = 100;
        this.retryDelay = 5000; // 5 seconds
        this.maxRetries = 3;
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize error manager
     */
    init() {
        // Get user ID if available
        this.loadUserId();
        
        // Set up online/offline listeners
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.flushErrorQueue();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
        
        // Set up global error handlers
        this.setupGlobalHandlers();
        
        // Flush any queued errors
        this.flushErrorQueue();
    }
    
    /**
     * Load user ID from various sources
     */
    async loadUserId() {
        try {
            // Try to get from user identification
            if (window.userIdentification && typeof window.userIdentification.getUserId === 'function') {
                const userId = await window.userIdentification.getUserId();
                if (userId) {
                    this.userId = userId;
                    return;
                }
            }
            
            // Try localStorage
            const storedUserId = localStorage.getItem('user_id');
            if (storedUserId) {
                this.userId = storedUserId;
                return;
            }
            
            // Try to get from backend
            const response = await fetch('/api/user/identify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.user_id) {
                    this.userId = data.user_id;
                    localStorage.setItem('user_id', data.user_id);
                }
            }
        } catch (error) {
            // Silent fail - user ID is optional
            console.warn('[ErrorManager] Could not load user ID:', error);
        }
    }
    
    /**
     * Generate session ID
     */
    generateSessionId() {
        let sessionId = sessionStorage.getItem('error_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('error_session_id', sessionId);
        }
        return sessionId;
    }
    
    /**
     * Set up global error handlers
     */
    setupGlobalHandlers() {
        // JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError({
                error_type: 'javascript',
                error_level: 'error',
                error_message: event.message || 'Unknown JavaScript error',
                error_stack: event.error ? event.error.stack : null,
                error_source: event.filename || 'unknown',
                error_line: event.lineno || null,
                error_column: event.colno || null,
                page_url: window.location.href,
                context_data: {
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent
                }
            });
        });
        
        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            const error = event.reason;
            this.handleError({
                error_type: 'javascript',
                error_level: 'error',
                error_message: error?.message || 'Unhandled promise rejection',
                error_stack: error?.stack || String(error),
                error_source: 'promise_rejection',
                page_url: window.location.href,
                context_data: {
                    timestamp: new Date().toISOString(),
                    rejection: String(error)
                }
            });
        });
    }
    
    /**
     * Handle an error
     * @param {Object} errorData - Error information
     */
    async handleError(errorData) {
        try {
            // Add default fields
            const fullErrorData = {
                ...errorData,
                user_id: this.userId,
                session_id: this.sessionId,
                page_url: errorData.page_url || window.location.href,
                user_agent: navigator.userAgent,
                timestamp: new Date().toISOString()
            };
            
            // Add tags if not provided
            if (!fullErrorData.tags) {
                fullErrorData.tags = this.extractTags(fullErrorData);
            }
            
            // Log to console (for development)
            if (errorData.error_level === 'critical' || errorData.error_level === 'error') {
                console.error('[ErrorManager]', fullErrorData);
            } else if (errorData.error_level === 'warning') {
                console.warn('[ErrorManager]', fullErrorData);
            }
            
            // Try to log to database
            await this.logToDatabase(fullErrorData);
            
            // Show user-friendly message if critical
            if (errorData.error_level === 'critical') {
                this.showUserMessage('A critical error occurred. Please refresh the page.', 'error');
            }
            
        } catch (error) {
            // If logging fails, queue it
            console.error('[ErrorManager] Failed to handle error:', error);
            this.queueError(errorData);
        }
    }
    
    /**
     * Extract tags from error data
     */
    extractTags(errorData) {
        const tags = [];
        
        // Add error type tag
        if (errorData.error_type) {
            tags.push(errorData.error_type);
        }
        
        // Extract tags from error message
        const message = errorData.error_message || '';
        if (message.includes('API') || message.includes('api') || message.includes('fetch')) {
            tags.push('api');
        }
        if (message.includes('404') || message.includes('not found')) {
            tags.push('404');
        }
        if (message.includes('network') || message.includes('Network')) {
            tags.push('network');
        }
        if (message.includes('points') || message.includes('Points')) {
            tags.push('points');
        }
        if (message.includes('battle') || message.includes('Battle')) {
            tags.push('battle');
        }
        
        // Extract from page URL
        const url = errorData.page_url || window.location.href;
        if (url.includes('/battle')) tags.push('battle');
        if (url.includes('/game')) tags.push('game');
        if (url.includes('/generator')) tags.push('generator');
        if (url.includes('/stats')) tags.push('stats');
        
        return tags;
    }
    
    /**
     * Log error to database
     */
    async logToDatabase(errorData) {
        if (!this.isOnline) {
            this.queueError(errorData);
            return;
        }
        
        try {
            // Try primary API base first
            let response = await fetch(this.apiBase + '/log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorData)
            });
            
            // If 404, try fallback
            if (response.status === 404 && this.apiBaseFallback) {
                response = await fetch(this.apiBaseFallback + '/log', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(errorData)
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const text = await response.text();
            try {
                return text ? JSON.parse(text) : {};
            } catch (e) {
                throw new Error(`Server returned non-JSON (${response.status})`);
            }
            
        } catch (error) {
            // Queue for retry
            this.queueError(errorData);
            throw error;
        }
    }
    
    /**
     * Queue error for later retry
     */
    queueError(errorData) {
        if (this.errorQueue.length >= this.maxQueueSize) {
            // Remove oldest error
            this.errorQueue.shift();
        }
        
        this.errorQueue.push({
            ...errorData,
            retryCount: 0,
            queuedAt: new Date().toISOString()
        });
    }
    
    /**
     * Flush error queue
     */
    async flushErrorQueue() {
        if (!this.isOnline || this.errorQueue.length === 0) {
            return;
        }
        
        const errorsToRetry = [...this.errorQueue];
        this.errorQueue = [];
        
        for (const errorData of errorsToRetry) {
            if (errorData.retryCount >= this.maxRetries) {
                console.warn('[ErrorManager] Max retries reached for error:', errorData);
                continue;
            }
            
            try {
                errorData.retryCount++;
                await this.logToDatabase(errorData);
            } catch (error) {
                // Re-queue if still failing
                this.queueError(errorData);
            }
        }
    }
    
    /**
     * Show user-friendly error message
     */
    showUserMessage(message, type = 'error') {
        // Try to use toast notifications if available
        if (window.toast && typeof window.toast[type] === 'function') {
            window.toast[type](message);
            return;
        }
        
        // Fallback to alert
        if (type === 'critical' || type === 'error') {
            console.error('[ErrorManager]', message);
        } else {
            console.warn('[ErrorManager]', message);
        }
    }
    
    /**
     * Log API error
     */
    logApiError(endpoint, method, status, errorMessage, responseBody = null) {
        return this.handleError({
            error_type: 'api',
            error_level: status >= 500 ? 'critical' : status >= 400 ? 'error' : 'warning',
            error_code: String(status),
            error_message: `API Error: ${method} ${endpoint} - ${errorMessage}`,
            request_method: method,
            request_url: endpoint,
            response_status: status,
            response_body: responseBody ? String(responseBody).substring(0, 1000) : null,
            tags: ['api', String(status)]
        });
    }
    
    /**
     * Log network error
     */
    logNetworkError(endpoint, method, errorMessage) {
        return this.handleError({
            error_type: 'network',
            error_level: 'error',
            error_message: `Network Error: ${method} ${endpoint} - ${errorMessage}`,
            request_method: method,
            request_url: endpoint,
            tags: ['network', 'api']
        });
    }
    
    /**
     * Log JavaScript error with context
     */
    logJSError(error, context = {}) {
        return this.handleError({
            error_type: 'javascript',
            error_level: 'error',
            error_message: error.message || String(error),
            error_stack: error.stack || null,
            error_source: context.source || 'unknown',
            error_line: context.line || null,
            error_column: context.column || null,
            context_data: context
        });
    }
    
    /**
     * Get error statistics
     */
    async getErrorStats(days = 7) {
        try {
            let response = await fetch(`${this.apiBase}/stats?days=${days}`);
            if (response.status === 404 && this.apiBaseFallback) {
                response = await fetch(`${this.apiBaseFallback}/stats?days=${days}`);
            }
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('[ErrorManager] Failed to get error stats:', error);
            return null;
        }
    }
    
    /**
     * Get error list
     */
    async getErrorList(options = {}) {
        try {
            const params = new URLSearchParams({
                limit: options.limit || 50,
                offset: options.offset || 0,
                ...options
            });
            
            let response = await fetch(`${this.apiBase}/list?${params}`);
            if (response.status === 404 && this.apiBaseFallback) {
                response = await fetch(`${this.apiBaseFallback}/list?${params}`);
            }
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('[ErrorManager] Failed to get error list:', error);
            return null;
        }
    }
}

// Create global instance
window.ErrorManager = new ErrorManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorManager;
}
