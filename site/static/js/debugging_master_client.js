/**
 * Debugging Master Client
 * Client-side integration for the debugging master system
 */
class DebuggingMasterClient {
    constructor() {
        this.sessionId = null;
        this.profileId = null;
        this.apiBase = window.DEBUGGING_MASTER_API_BASE || '/api/debugging';
        this.apiFallback = window.DEBUGGING_MASTER_API_FALLBACK || '/api/debugging';
        this.initialized = false;
    }
    
    async initialize() {
        if (this.initialized) return;
        
        try {
            // Collect browser data
            const browserData = this.collectBrowserData();
            
            // Start debug session
            const fetchOpts = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    browser_data: browserData,
                    metadata: {
                        'url': window.location.href,
                        'referrer': document.referrer,
                        'timestamp': new Date().toISOString()
                    }
                })
            };
            if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
                fetchOpts.signal = AbortSignal.timeout(20000);
            }
            const response = await fetch(`${this.apiBase}/session/start`, fetchOpts);
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.sessionId = data.session.session_id;
                    this.profileId = data.profile.profile_id;
                    this.initialized = true;
                    
                    console.log('[Debugging Master] Session started:', this.sessionId);
                    
                    // Track page unload
                    window.addEventListener('beforeunload', () => {
                        this.endSession();
                    });
                }
            }
        } catch (error) {
            console.error('[Debugging Master] Initialization error:', error);
        }
    }
    
    collectBrowserData() {
        return {
            user_agent: navigator.userAgent,
            browser_name: this.getBrowserName(),
            browser_version: this.getBrowserVersion(),
            os_name: this.getOSName(),
            os_version: this.getOSVersion(),
            device_type: this.getDeviceType(),
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            },
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language,
            languages: navigator.languages || [navigator.language],
            plugins: Array.from(navigator.plugins).map(p => ({
                name: p.name,
                description: p.description
            })),
            canvas_fingerprint: this.getCanvasFingerprint(),
            webgl_fingerprint: this.getWebGLFingerprint(),
            audio_fingerprint: this.getAudioFingerprint()
        };
    }
    
    getBrowserName() {
        const ua = navigator.userAgent;
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        return 'Unknown';
    }
    
    getBrowserVersion() {
        const ua = navigator.userAgent;
        const match = ua.match(/(Chrome|Firefox|Safari|Edge)\/(\d+)/);
        return match ? match[2] : 'Unknown';
    }
    
    getOSName() {
        const ua = navigator.userAgent;
        if (ua.includes('Windows')) return 'Windows';
        if (ua.includes('Mac')) return 'macOS';
        if (ua.includes('Linux')) return 'Linux';
        if (ua.includes('Android')) return 'Android';
        if (ua.includes('iOS')) return 'iOS';
        return 'Unknown';
    }
    
    getOSVersion() {
        const ua = navigator.userAgent;
        const match = ua.match(/(Windows|Mac OS X|Linux|Android|iOS)[\s\/]?([\d\.]+)/);
        return match ? match[2] : 'Unknown';
    }
    
    getDeviceType() {
        const ua = navigator.userAgent;
        if (/Mobile|Android|iPhone|iPad/.test(ua)) return 'mobile';
        if (/Tablet|iPad/.test(ua)) return 'tablet';
        return 'desktop';
    }
    
    getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('Debugging Master', 2, 2);
            return canvas.toDataURL().substring(0, 100);
        } catch (e) {
            return '';
        }
    }
    
    getWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (!gl) return '';
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                return gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL).substring(0, 50);
            }
            return '';
        } catch (e) {
            return '';
        }
    }
    
    getAudioFingerprint() {
        // Simplified audio fingerprint
        return navigator.mediaDevices ? 'available' : 'unavailable';
    }
    
    async logAction(actionType, actionName, options = {}) {
        if (!this.sessionId) {
            await this.initialize();
        }
        
        if (!this.sessionId) return;
        
        const startTime = performance.now();
        
        try {
            // Use AI to predict error likelihood before action
            let aiPrediction = null;
            try {
                const predictResponse = await fetch(`${this.apiBase.replace('/debugging', '/ai/debugging')}/sessions/${this.sessionId}/predict-error`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action_type: actionType })
                });
                if (predictResponse.ok) {
                    aiPrediction = await predictResponse.json();
                }
            } catch (e) {
                // AI prediction is optional
            }
            
            const response = await fetch(`${this.apiBase}/action/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    action_type: actionType,
                    action_name: actionName,
                    target_tab: options.tab,
                    target_element: options.element,
                    result: options.result,
                    success: options.success !== false,
                    error_message: options.error,
                    execution_time_ms: Math.round(performance.now() - startTime),
                    metadata: {
                        ...(options.metadata || {}),
                        ai_prediction: aiPrediction?.prediction
                    }
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error logging action:', error);
        }
    }
    
    async logError(errorType, errorMessage, options = {}) {
        if (!this.sessionId) {
            await this.initialize();
        }
        
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`${this.apiBase}/error/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    error_type: errorType,
                    error_message: errorMessage,
                    error_stack: options.stack,
                    file_path: options.file,
                    line_number: options.line,
                    severity: options.severity || 'error',
                    metadata: options.metadata || {}
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error logging error:', error);
        }
    }
    
    async logPerformance(metricName, metricValue, options = {}) {
        if (!this.sessionId) {
            await this.initialize();
        }
        
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`${this.apiBase}/performance/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    metric_name: metricName,
                    metric_value: metricValue,
                    unit: options.unit,
                    context: options.context || {}
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error logging performance:', error);
        }
    }
    
    async endSession() {
        if (!this.sessionId) return;
        
        try {
            await fetch(`${this.apiBase}/session/end`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });
            
            this.sessionId = null;
            this.initialized = false;
        } catch (error) {
            console.error('[Debugging Master] Error ending session:', error);
        }
    }
    
    async getStats() {
        try {
            const response = await fetch(`${this.apiBase}/stats`);
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error getting stats:', error);
        }
        return null;
    }
    
    async getAIIntelligence() {
        try {
            const response = await fetch(`${this.apiBase.replace('/debugging', '/ai')}/intelligence/summary`);
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error getting AI intelligence:', error);
        }
        return null;
    }
    
    async getAIInsights() {
        try {
            const response = await fetch(`${this.apiBase.replace('/debugging', '/ai')}/insights`);
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('[Debugging Master] Error getting AI insights:', error);
        }
        return null;
    }
}

// Global instance
window.debuggingMaster = new DebuggingMasterClient();

// Auto-initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.debuggingMaster.initialize();
    });
} else {
    window.debuggingMaster.initialize();
}

// Global error handler
window.addEventListener('error', (event) => {
    window.debuggingMaster.logError(
        'javascript_error',
        event.message,
        {
            file: event.filename,
            line: event.lineno,
            stack: event.error?.stack,
            severity: 'error'
        }
    );
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    window.debuggingMaster.logError(
        'unhandled_promise_rejection',
        event.reason?.message || String(event.reason),
        {
            stack: event.reason?.stack,
            severity: 'error'
        }
    );
});
