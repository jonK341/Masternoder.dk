/**
 * User Identification Utility
 * Handles user identification and replaces default_user fallbacks
 */

class UserIdentification {
    constructor() {
        this.apiBase = '/api';
        this.userId = null;
        this.identificationPromise = null;
    }

    /**
     * Initialize user identification
     * Call this on page load
     */
    async initialize() {
        if (this.identificationPromise) {
            return this.identificationPromise;
        }

        this.identificationPromise = this._identifyUser();
        return this.identificationPromise;
    }

    /**
     * Identify or create user
     */
    async _identifyUser() {
        // Check localStorage first
        const storedUserId = localStorage.getItem('game_user_id') || 
                            localStorage.getItem('user_id');
        
        if (this._isUsableUserId(storedUserId)) {
            // Verify user exists
            try {
                const verifyResponse = await fetch(`${this.apiBase}/user/profile/${storedUserId}/display`);
                if (verifyResponse.ok) {
                    const verifyData = await verifyResponse.json();
                    if (verifyData.success) {
                        this.userId = storedUserId;
                        return storedUserId;
                    }
                }
            } catch (e) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'user-identification.js', context: 'catch' }); }
                // Continue to identification if verification fails
            }
        }

        // Get device fingerprint
        const fingerprint = this.getDeviceFingerprint();
        
        // Collect identification data
        const identificationData = {
            device_fingerprint: fingerprint,
            browser_fingerprint: this.getBrowserFingerprint(),
            screen_width: window.screen.width,
            screen_height: window.screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language,
            localstorage_user_id: storedUserId,
            referer: document.referrer || '',
            landing_page: window.location.pathname
        };

        try {
            // Call identification API
            const response = await fetch(`${this.apiBase}/user/identify/simple`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(identificationData)
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && this._isUsableUserId(data.user_id)) {
                    this.userId = String(data.user_id).trim();
                    
                    // Store in localStorage
                    localStorage.setItem('game_user_id', this.userId);
                    localStorage.setItem('user_id', this.userId);
                    
                    // Store identification timestamp
                    localStorage.setItem('user_identified_at', new Date().toISOString());
                    
                    return data.user_id;
                }
            }
        } catch (error) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(error instanceof Error ? error : new Error(String(error)), { source: 'user-identification.js', context: 'catch' }); }
            console.warn('Error identifying user:', error);
        }

        this.userId = null;
        return null;
    }

    _isUsableUserId(id) {
        if (window.MnUserId && typeof window.MnUserId.isUsable === 'function') {
            return window.MnUserId.isUsable(id);
        }
        if (typeof id !== 'string') return false;
        const value = id.trim();
        if (!value || value === '[object Promise]') return false;
        const lowered = value.toLowerCase();
        return lowered !== 'default_user' && lowered !== 'undefined' && lowered !== 'null';
    }

    /**
     * Get current user ID (synchronous)
     * Returns stored user ID or null if not identified yet
     */
    getUserIdSync() {
        if (this.userId) {
            return this.userId;
        }
        
        const stored = localStorage.getItem('game_user_id') || 
                      localStorage.getItem('user_id');
        
        if (this._isUsableUserId(stored)) {
            return stored.trim();
        }
        
        return null;
    }

    /**
     * Get current user ID (async - ensures identification)
     */
    async getUserId() {
        if (this._isUsableUserId(this.userId)) {
            return this.userId.trim();
        }

        await this.initialize();
        return this._isUsableUserId(this.userId) ? this.userId.trim() : null;
    }

    /**
     * Get device fingerprint
     */
    getDeviceFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Fingerprint', 2, 2);
        
        const fingerprint = [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height,
            new Date().getTimezoneOffset(),
            canvas.toDataURL()
        ].join('|');
        
        // Simple hash
        let hash = 0;
        for (let i = 0; i < fingerprint.length; i++) {
            const char = fingerprint.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        
        return Math.abs(hash).toString(36);
    }

    /**
     * Get browser fingerprint
     */
    getBrowserFingerprint() {
        return [
            navigator.userAgent,
            navigator.platform,
            navigator.cookieEnabled,
            navigator.doNotTrack,
            screen.colorDepth,
            screen.pixelDepth
        ].join('|');
    }
}

// Global instance
const userIdentification = new UserIdentification();

// Auto-initialize on page load
if (typeof window !== 'undefined') {
    // Initialize immediately but don't block
    userIdentification.initialize().catch(err => {
        if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('console.error'), { source: 'user-identification.js', context: 'console.error' }); }
        console.error('User identification initialization failed:', err);
    });
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = userIdentification;
}
