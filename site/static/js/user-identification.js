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
        
        if (storedUserId && storedUserId !== 'default_user') {
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
            } catch (e) {
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
                if (data.success && data.user_id) {
                    this.userId = data.user_id;
                    
                    // Store in localStorage
                    localStorage.setItem('game_user_id', data.user_id);
                    localStorage.setItem('user_id', data.user_id);
                    
                    // Store identification timestamp
                    localStorage.setItem('user_identified_at', new Date().toISOString());
                    
                    return data.user_id;
                }
            }
        } catch (error) {
            console.error('Error identifying user:', error);
        }

        // Fallback to default_user only if identification completely fails
        this.userId = 'default_user';
        return 'default_user';
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
        
        if (stored && stored !== 'default_user') {
            return stored;
        }
        
        return null;
    }

    /**
     * Get current user ID (async - ensures identification)
     */
    async getUserId() {
        if (this.userId) {
            return this.userId;
        }

        await this.initialize();
        return this.userId;
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
        console.error('User identification initialization failed:', err);
    });
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = userIdentification;
}
