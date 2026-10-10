/**
 * Backend Connector
 * Unified JavaScript module for connecting frontend to backend APIs
 * Handles all API calls, error handling, and data formatting
 */

class BackendConnector {
    constructor() {
        this.apiBase = '/api';
        this.userId = null; // Will be set after identification
        this.cache = new Map();
        this.cacheTimeout = 60000; // 1 minute
        this.retryDelays = [1000, 2000, 5000]; // Exponential backoff delays
        this.maxRetries = 3;
        this.identificationPromise = null;
        
        // Initialize user identification
        this.initializeUser();
    }

    /**
     * Initialize user identification
     */
    async initializeUser() {
        if (this.identificationPromise) {
            return this.identificationPromise;
        }

        this.identificationPromise = this._identifyUser();
        try {
            this.userId = await this.identificationPromise;
        } catch (error) {
            console.warn('User identification failed:', error);
            this.userId = null;
        }
        return this.userId;
    }

    /**
     * Identify or get user ID
     */
    async _identifyUser() {
        // Check if user-identification.js is loaded
        if (typeof userIdentification !== 'undefined') {
            return await userIdentification.getUserId();
        }

        // Fallback: check localStorage
        const stored = localStorage.getItem('game_user_id') || 
                      localStorage.getItem('user_id');
        
        if (this._isCanonicalUserId(stored)) {
            return stored.trim();
        }

        // Try to identify via API
        try {
            const fingerprint = this._getSimpleFingerprint();
            const response = await fetch(`${this.apiBase}/user/identify/simple`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_fingerprint: fingerprint,
                    screen_width: window.screen.width,
                    screen_height: window.screen.height,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    language: navigator.language
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && this._isCanonicalUserId(data.user_id)) {
                    const resolved = String(data.user_id).trim();
                    localStorage.setItem('game_user_id', resolved);
                    localStorage.setItem('user_id', resolved);
                    return resolved;
                }
            }
        } catch (error) {
            console.warn('User identification API call failed:', error);
        }

        return null;
    }

    /**
     * Get simple fingerprint
     */
    _getSimpleFingerprint() {
        return [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height
        ].join('|');
    }

    /**
     * Get user ID (async - ensures identification)
     */
    _isCanonicalUserId(id) {
        return typeof id === 'string' && /^user_[A-Za-z0-9_]{4,120}$/.test(id.trim());
    }

    async _requireUserId(userId) {
        let uid = userId;
        if (uid != null && typeof uid.then === 'function') {
            uid = await uid;
        }
        if (!this._isCanonicalUserId(uid)) {
            uid = await this.getUserId();
        }
        if (!this._isCanonicalUserId(uid)) {
            return null;
        }
        return String(uid).trim();
    }

    _skippedUser() {
        return { success: false, skipped: true, error: 'canonical user id unavailable' };
    }

    async getUserId() {
        if (this._isCanonicalUserId(this.userId)) {
            return this.userId.trim();
        }
        
        await this.initializeUser();
        return this._isCanonicalUserId(this.userId) ? this.userId.trim() : null;
    }

    /**
     * Get user ID synchronously (may return null if not identified yet)
     */
    getUserIdSync() {
        if (this.userId) {
            return this.userId;
        }
        
        const stored = localStorage.getItem('game_user_id') || 
                      localStorage.getItem('user_id');
        
        return this._isCanonicalUserId(stored) ? stored.trim() : null;
    }

    /**
     * Generic API fetch with error handling and exponential backoff
     */
    async fetchAPI(endpoint, options = {}, retryCount = 0) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.apiBase}${endpoint}`;
        const cacheKey = `${url}_${JSON.stringify(options)}`;
        
        // Check cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }

        try {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
                ...options
            };

            const response = await fetch(url, defaultOptions);
            
            // Handle non-OK responses more gracefully
            if (!response.ok) {
                // Try to parse error response as JSON first
                let errorData;
                let responseBody = null;
                const contentType = response.headers.get('Content-Type') || '';
                
                if (contentType.includes('application/json')) {
                    try {
                        errorData = await response.json();
                        responseBody = JSON.stringify(errorData);
                        // If we got JSON error, log it and return it (don't retry)
                        if (window.ErrorManager) {
                            window.ErrorManager.logApiError(
                                url,
                                options.method || 'GET',
                                response.status,
                                errorData?.error || errorData?.message || response.statusText,
                                responseBody
                            );
                        }
                        return errorData;
                    } catch (e) {
                        // JSON parse failed, continue to retry logic
                        try {
                            responseBody = await response.text();
                        } catch (e2) {
                            // Can't read body
                        }
                    }
                } else {
                    // Try to read as text
                    try {
                        responseBody = await response.text();
                    } catch (e) {
                        // Can't read body
                    }
                }
                
                // Log API error
                if (window.ErrorManager) {
                    window.ErrorManager.logApiError(
                        url,
                        options.method || 'GET',
                        response.status,
                        response.statusText,
                        responseBody
                    );
                }
                
                // If HTML response or JSON parse failed, check if we should retry
                if (retryCount < this.maxRetries && response.status >= 500) {
                    // Server error - retry with exponential backoff
                    const delay = this.retryDelays[retryCount] || this.retryDelays[this.retryDelays.length - 1];
                    await new Promise(resolve => setTimeout(resolve, delay));
                    return this.fetchAPI(endpoint, options, retryCount + 1);
                }
                
                // Return structured error
                return {
                    success: false,
                    error: errorData?.error || `API Error: ${response.status} ${response.statusText}`,
                    status: response.status,
                    message: errorData?.message || 'Request failed'
                };
            }

            const data = await response.json();
            
            // Cache successful responses
            if (data.success !== false) {
                this.cache.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
            }

            return data;
        } catch (error) {
            // Network error - retry if possible
            if (retryCount < this.maxRetries && error.name !== 'AbortError') {
                const delay = this.retryDelays[retryCount] || this.retryDelays[this.retryDelays.length - 1];
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.fetchAPI(endpoint, options, retryCount + 1);
            }
            
            // Log network error
            if (window.ErrorManager) {
                window.ErrorManager.logNetworkError(url, options.method || 'GET', error.message);
            } else {
                console.error(`API Error [${endpoint}]:`, error);
            }
            
            return {
                success: false,
                error: error.message || 'Network error',
                retries: retryCount
            };
        }
    }
    
    /**
     * Clear cache
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * USER PROFILE APIs
     */
    async getUserProfile(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/profile/' + encodeURIComponent(uid));
    }

    async getUserProfileDisplay(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/profile/' + encodeURIComponent(uid) + '/display');
    }

    /**
     * Single-call profile: profile + skills + stats + activity + agents + achievements + trophies + geo.
     * Use this for the profile page to avoid many loading states.
     */
    async getUserProfileAggregated(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/profile/' + encodeURIComponent(uid) + '/aggregated');
    }

    async createUser(userData) {
        return await this.fetchAPI('/user/create', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    async updateUserProfile(updateData) {
        const uid = await this._requireUserId(null);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/profile/update', {
            method: 'POST',
            body: JSON.stringify({
                user_id: uid,
                update_data: updateData
            })
        });
    }

    /**
     * ONBOARDING APIs
     */
    async getOnboardingStatus(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/onboarding/status/' + encodeURIComponent(uid));
    }

    async startOnboarding(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/onboarding/start', {
            method: 'POST',
            body: JSON.stringify({ user_id: uid })
        });
    }

    async completeOnboardingStep(stepName, userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/onboarding/complete-step', {
            method: 'POST',
            body: JSON.stringify({
                user_id: uid,
                step_name: stepName
            })
        });
    }

    async getOnboardingProgress(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/onboarding/progress/' + encodeURIComponent(uid));
    }

    /**
     * AGENT SKILLS APIs
     */
    async getUserAgentSkills(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/user/agent-skills/' + encodeURIComponent(uid));
    }

    async getAgentControllerStatus() {
        return await this.fetchAPI('/agents/controller/status');
    }

    async getAgentSkillsetStats() {
        return await this.fetchAPI('/agents/skillsets/stats');
    }

    /**
     * GAME SYSTEM APIs
     */
    async getPlayerLevel(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/game/hunters/level?user_id=' + encodeURIComponent(uid));
    }

    async getXPHistory(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/game/hunters/xp-history?user_id=' + encodeURIComponent(uid));
    }

    async getDailyActivities(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/game/daily-activities?user_id=' + encodeURIComponent(uid));
    }

    /**
     * SHOP APIs
     */
    async getShopCurrency(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/shop/currency?user_id=' + encodeURIComponent(uid));
    }

    /**
     * POINTS APIs
     */
    async getAllPoints(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/points/all?user_id=' + encodeURIComponent(uid));
    }

    /**
     * REWARDS APIs
     */
    async getRewards(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/game/hunters/rewards?user_id=' + encodeURIComponent(uid));
    }

    async claimReward(rewardId, userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/game/hunters/rewards/claim', {
            method: 'POST',
            body: JSON.stringify({
                user_id: uid,
                reward_id: rewardId
            })
        });
    }

    /**
     * STATS APIs
     */
    async getStats(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        const result = await this.fetchAPI('/user/profile/' + encodeURIComponent(uid) + '/stats');
        if (result && result.success) {
            return result;
        }
        // Fallback: get stats from profile display
        const profileData = await this.getUserProfileDisplay(uid);
        if (profileData && profileData.success && profileData.stats) {
            return {
                success: true,
                stats: profileData.stats
            };
        }
        return { success: false, error: 'Stats not available' };
    }

    /**
     * SOCIAL APIs
     */
    async getSocialData(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/social/user/' + encodeURIComponent(uid));
    }

    /**
     * ANALYTICS APIs
     */
    async getAnalytics(userId = null) {
        const uid = await this._requireUserId(userId);
        if (!uid) return this._skippedUser();
        return await this.fetchAPI('/analytics/user/' + encodeURIComponent(uid));
    }

    /**
     * Clear cache
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * Clear cache for specific endpoint
     */
    clearCacheFor(endpoint) {
        for (const [key] of this.cache) {
            if (key.includes(endpoint)) {
                this.cache.delete(key);
            }
        }
    }
}

// Create global instance
const backendConnector = new BackendConnector();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BackendConnector;
}
