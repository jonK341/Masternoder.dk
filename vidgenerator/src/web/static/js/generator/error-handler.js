/**
 * Enhanced Error Handler for Generator
 * Provides user-friendly error messages and recovery options
 */

class GeneratorErrorHandler {
    constructor() {
        this.errorModal = null;
        this.init();
    }
    
    init() {
        this.createErrorModal();
    }
    
    createErrorModal() {
        // Create modal HTML
        const modalHTML = `
            <div id="generator-error-modal" class="error-modal" style="display: none;">
                <div class="error-modal-overlay"></div>
                <div class="error-modal-content">
                    <div class="error-modal-header">
                        <h3 class="error-title">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span id="error-title-text">Error</span>
                        </h3>
                        <button class="error-modal-close" onclick="generatorErrorHandler.closeModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="error-modal-body">
                        <div class="error-icon" id="error-icon"></div>
                        <p class="error-message" id="error-message"></p>
                        <div class="error-details" id="error-details" style="display: none;">
                            <pre id="error-details-text"></pre>
                        </div>
                        <div class="error-actions" id="error-actions"></div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert into body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.errorModal = document.getElementById('generator-error-modal');
    }
    
    handleError(error, context = {}) {
        console.error('[GeneratorError]', error, context);
        
        const errorInfo = this.categorizeError(error, context);
        this.showError(errorInfo);
    }
    
    categorizeError(error, context) {
        const errorMessage = error.message || String(error);
        const errorString = errorMessage.toLowerCase();
        
        // Network errors
        if (errorString.includes('network') || 
            errorString.includes('fetch') || 
            errorString.includes('connection') ||
            errorString.includes('timeout') ||
            error.name === 'TypeError' && errorString.includes('failed')) {
            return {
                type: 'network',
                title: 'Connection Error',
                message: 'Unable to connect to the server. Please check your internet connection.',
                icon: 'fa-wifi',
                color: 'orange',
                actions: [
                    { label: 'Retry', action: 'retry', primary: true },
                    { label: 'Check Connection', action: 'checkConnection' }
                ],
                canRetry: true
            };
        }
        
        // Validation errors
        if (errorString.includes('validation') || 
            errorString.includes('invalid') ||
            errorString.includes('required') ||
            errorString.includes('too short') ||
            errorString.includes('too long')) {
            return {
                type: 'validation',
                title: 'Invalid Input',
                message: errorMessage || 'Please check your input and try again.',
                icon: 'fa-exclamation-circle',
                color: 'yellow',
                actions: [
                    { label: 'OK', action: 'close', primary: true }
                ],
                canRetry: false
            };
        }
        
        // Server errors (5xx)
        if (context.status >= 500 || 
            errorString.includes('server error') ||
            errorString.includes('internal error')) {
            return {
                type: 'server',
                title: 'Server Error',
                message: 'The server encountered an error. Our team has been notified.',
                icon: 'fa-server',
                color: 'red',
                actions: [
                    { label: 'Retry', action: 'retry', primary: true },
                    { label: 'Report Issue', action: 'report', primary: false }
                ],
                canRetry: true
            };
        }
        
        // Client errors (4xx)
        if (context.status >= 400 && context.status < 500) {
            return {
                type: 'client',
                title: 'Request Error',
                message: errorMessage || 'Your request could not be processed.',
                icon: 'fa-ban',
                color: 'red',
                actions: [
                    { label: 'OK', action: 'close', primary: true },
                    { label: 'Report Issue', action: 'report', primary: false }
                ],
                canRetry: false
            };
        }
        
        // Timeout errors
        if (errorString.includes('timeout') || 
            errorString.includes('timed out')) {
            return {
                type: 'timeout',
                title: 'Request Timeout',
                message: 'The request took too long to complete. The server may be busy.',
                icon: 'fa-clock',
                color: 'orange',
                actions: [
                    { label: 'Retry', action: 'retry', primary: true },
                    { label: 'Wait & Retry', action: 'waitRetry' }
                ],
                canRetry: true
            };
        }
        
        // Unknown errors
        return {
            type: 'unknown',
            title: 'Unexpected Error',
            message: errorMessage || 'An unexpected error occurred.',
            icon: 'fa-question-circle',
            color: 'gray',
            actions: [
                { label: 'OK', action: 'close', primary: true },
                { label: 'Show Details', action: 'showDetails' },
                { label: 'Report Issue', action: 'report', primary: false }
            ],
            canRetry: false,
            error: error
        };
    }
    
    showError(errorInfo) {
        const titleEl = document.getElementById('error-title-text');
        const messageEl = document.getElementById('error-message');
        const iconEl = document.getElementById('error-icon');
        const actionsEl = document.getElementById('error-actions');
        const detailsEl = document.getElementById('error-details');
        const detailsTextEl = document.getElementById('error-details-text');
        
        // Set title and message
        titleEl.textContent = errorInfo.title;
        messageEl.textContent = errorInfo.message;
        
        // Set icon
        iconEl.className = `error-icon error-icon-${errorInfo.color}`;
        iconEl.innerHTML = `<i class="fas ${errorInfo.icon}"></i>`;
        
        // Create action buttons
        actionsEl.innerHTML = '';
        errorInfo.actions.forEach(action => {
            const btn = document.createElement('button');
            btn.className = `error-action-btn ${action.primary ? 'primary' : 'secondary'}`;
            btn.textContent = action.label;
            btn.onclick = () => this.handleAction(action.action, errorInfo);
            actionsEl.appendChild(btn);
        });
        
        // Store error info for actions
        this.currentError = errorInfo;
        
        // Show modal
        this.errorModal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
    
    handleAction(action, errorInfo) {
        switch (action) {
            case 'close':
                this.closeModal();
                break;
                
            case 'retry':
                this.closeModal();
                if (window.simplifiedGenerator && errorInfo.canRetry) {
                    // Trigger retry in generator
                    if (window.simplifiedGenerator.retryLastOperation) {
                        window.simplifiedGenerator.retryLastOperation();
                    }
                }
                break;
                
            case 'waitRetry':
                this.closeModal();
                setTimeout(() => {
                    if (window.simplifiedGenerator && errorInfo.canRetry) {
                        if (window.simplifiedGenerator.retryLastOperation) {
                            window.simplifiedGenerator.retryLastOperation();
                        }
                    }
                }, 5000);
                break;
                
            case 'checkConnection':
                // Test connection
                fetch('/vidgenerator/api/health', { method: 'GET' })
                    .then(() => {
                        this.showSuccess('Connection is working!');
                        this.closeModal();
                    })
                    .catch(() => {
                        this.showError({
                            type: 'network',
                            title: 'No Connection',
                            message: 'Cannot reach the server. Please check your internet connection.',
                            icon: 'fa-wifi',
                            color: 'red',
                            actions: [{ label: 'OK', action: 'close', primary: true }]
                        });
                    });
                break;
                
            case 'showDetails':
                const detailsEl = document.getElementById('error-details');
                const detailsTextEl = document.getElementById('error-details-text');
                if (detailsEl.style.display === 'none') {
                    detailsTextEl.textContent = JSON.stringify(errorInfo.error || errorInfo, null, 2);
                    detailsEl.style.display = 'block';
                } else {
                    detailsEl.style.display = 'none';
                }
                break;
                
            case 'report':
                // Open issue reporting (could integrate with support system)
                const reportData = {
                    error: errorInfo,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href
                };
                console.log('[ErrorReport]', reportData);
                // TODO: Send to backend for logging
                this.showSuccess('Issue reported. Thank you!');
                this.closeModal();
                break;
        }
    }
    
    showSuccess(message) {
        // Quick success notification
        const notification = document.createElement('div');
        notification.className = 'error-success-notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    closeModal() {
        this.errorModal.style.display = 'none';
        document.body.style.overflow = '';
        this.currentError = null;
    }
}

// Global instance
const generatorErrorHandler = new GeneratorErrorHandler();

// Make available globally
if (typeof window !== 'undefined') {
    window.generatorErrorHandler = generatorErrorHandler;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GeneratorErrorHandler;
}

