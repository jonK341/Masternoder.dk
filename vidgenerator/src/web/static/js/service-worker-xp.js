/**
 * Service Worker XP System Integration
 * Behavioral tracking and psychological profiling in service worker
 */

// XP System for Service Worker
class ServiceWorkerXPSystem {
    constructor() {
        this.storageKey = 'sw_xp_system';
        this.data = this.loadData();
        this.defenseSystem = new ServiceWorkerDefenseSystem();
    }

    loadData() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored ? JSON.parse(stored) : {
                behavioral: {},
                xp_history: {},
                psychological: {},
                last_sync: null
            };
        } catch (e) {
            console.warn('[SW-XP] Failed to load data:', e);
            return { behavioral: {}, xp_history: {}, psychological: {}, last_sync: null };
        }
    }

    saveData() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.data));
        } catch (e) {
            console.warn('[SW-XP] Failed to save data:', e);
        }
    }

    trackAction(userId, actionType, metadata = {}) {
        const timestamp = new Date().toISOString();
        
        // Initialize user data if needed
        if (!this.data.behavioral[userId]) {
            this.data.behavioral[userId] = {
                total_xp: 0,
                level: 1,
                actions: {},
                last_active: timestamp,
                session_count: 0,
                total_generations: 0
            };
        }

        // XP values
        const xpValues = {
            'generate_video': 100,
            'watch_video': 10,
            'share_video': 25,
            'complete_generation': 50,
            'return_user': 5
        };

        const xpAwarded = xpValues[actionType] || 5;
        this.data.behavioral[userId].total_xp += xpAwarded;
        this.data.behavioral[userId].actions[actionType] = (this.data.behavioral[userId].actions[actionType] || 0) + 1;
        this.data.behavioral[userId].last_active = timestamp;
        this.data.behavioral[userId].level = Math.floor(this.data.behavioral[userId].total_xp / 1000) + 1;

        // Record XP event
        if (!this.data.xp_history[userId]) {
            this.data.xp_history[userId] = [];
        }
        this.data.xp_history[userId].push({
            timestamp,
            action_type: actionType,
            xp_awarded: xpAwarded,
            metadata
        });

        // Update psychological profile
        this.updatePsychologicalProfile(userId, actionType, metadata);

        this.saveData();
        return xpAwarded;
    }

    updatePsychologicalProfile(userId, actionType, metadata) {
        if (!this.data.psychological[userId]) {
            this.data.psychological[userId] = {
                creativity_level: 0.5,
                patience_level: 0.5,
                detail_orientation: 0.5,
                preferred_complexity: 0.5,
                attention_span: 0.5,
                optimization_hints: {}
            };
        }

        const profile = this.data.psychological[userId];

        // Update based on actions
        if (actionType === 'generate_video') {
            if (metadata.prompt_length) {
                const complexity = Math.min(metadata.prompt_length / 500, 1.0);
                profile.preferred_complexity = (profile.preferred_complexity * 0.9) + (complexity * 0.1);
            }
            if (metadata.retry_count) {
                const patience = Math.max(0, 1.0 - (metadata.retry_count * 0.1));
                profile.patience_level = (profile.patience_level * 0.9) + (patience * 0.1);
            }
        }

        // Generate optimization hints
        profile.optimization_hints = this.generateOptimizationHints(profile);
    }

    generateOptimizationHints(profile) {
        const hints = {
            preferred_clip_duration: 10,
            preferred_documentary_duration: 300,
            complexity_level: profile.preferred_complexity,
            optimization_priority: 'balanced'
        };

        if (profile.patience_level < 0.3) {
            hints.optimization_priority = 'speed';
        } else if (profile.detail_orientation > 0.7) {
            hints.optimization_priority = 'quality';
        }

        const attention = profile.attention_span || 0.5;
        if (attention < 0.3) {
            hints.preferred_clip_duration = 5;
            hints.preferred_documentary_duration = 180;
        } else if (attention > 0.7) {
            hints.preferred_clip_duration = 15;
            hints.preferred_documentary_duration = 600;
        }

        return hints;
    }

    getUserProfile(userId) {
        return {
            behavioral: this.data.behavioral[userId] || {},
            psychological: this.data.psychological[userId] || {},
            optimization_hints: this.data.psychological[userId]?.optimization_hints || {}
        };
    }

    getGenerationRecommendations(userId) {
        const profile = this.getUserProfile(userId);
        const hints = profile.optimization_hints;

        return {
            clip_duration_range: [
                Math.max(5, hints.preferred_clip_duration - 5),
                Math.min(15, hints.preferred_clip_duration + 5)
            ],
            target_duration_range: [
                Math.max(180, hints.preferred_documentary_duration - 120),
                Math.min(600, hints.preferred_documentary_duration + 120)
            ],
            complexity_level: hints.complexity_level || 0.5,
            optimization_priority: hints.optimization_priority || 'balanced'
        };
    }
}

// AI Defense System for Service Worker
class ServiceWorkerDefenseSystem {
    constructor() {
        this.blockedPatterns = [
            /<script[^>]*>.*?<\/script>/gi,
            /javascript:/gi,
            /on\w+\s*=/gi
        ];
        this.rateLimits = {};
    }

    analyzeInput(userId, inputText) {
        const threats = [];
        let threatLevel = 0;

        // Check patterns
        for (const pattern of this.blockedPatterns) {
            if (pattern.test(inputText)) {
                threats.push({ pattern: pattern.toString(), level: 'high' });
                threatLevel = Math.max(threatLevel, 2);
            }
        }

        // Check rate limit
        if (!this.checkRateLimit(userId, 'generate')) {
            threats.push({ type: 'rate_limit', level: 'medium' });
            threatLevel = Math.max(threatLevel, 1);
        }

        return {
            safe: threatLevel === 0,
            threat_level: threatLevel,
            threats,
            action: threatLevel >= 2 ? 'block' : threatLevel >= 1 ? 'monitor' : 'allow'
        };
    }

    checkRateLimit(userId, actionType) {
        const key = `${userId}:${actionType}`;
        const now = Date.now();
        const limit = 10; // 10 per hour
        const window = 3600000; // 1 hour

        if (!this.rateLimits[key] || (now - this.rateLimits[key].resetTime) > window) {
            this.rateLimits[key] = { count: 0, resetTime: now };
        }

        if (this.rateLimits[key].count >= limit) {
            return false;
        }

        this.rateLimits[key].count++;
        return true;
    }

    sanitizeInput(inputText) {
        let sanitized = inputText;
        
        // Remove script tags
        sanitized = sanitized.replace(/<script[^>]*>.*?<\/script>/gi, '');
        
        // Remove javascript: protocol
        sanitized = sanitized.replace(/javascript:/gi, '');
        
        // Remove event handlers
        sanitized = sanitized.replace(/on\w+\s*=/gi, '');
        
        // Limit length
        const maxLength = 10000;
        if (sanitized.length > maxLength) {
            sanitized = sanitized.substring(0, maxLength);
        }

        return sanitized.trim();
    }
}

// Initialize XP system in service worker
const swXPSystem = new ServiceWorkerXPSystem();

// Intercept fetch requests for behavioral tracking
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Track generation requests
    if (url.pathname.includes('/api/documentary/generate')) {
        event.respondWith(
            (async () => {
                try {
                    // Get user ID from request (or generate one)
                    const userId = self.getUserId() || 'anonymous';
                    
                    // Clone request to read body
                    const clonedRequest = event.request.clone();
                    const body = await clonedRequest.json().catch(() => ({}));
                    
                    // AI Defense: Analyze and sanitize input
                    const defenseResult = swXPSystem.defenseSystem.analyzeInput(userId, body.prompt || '');
                    
                    if (!defenseResult.safe && defenseResult.action === 'block') {
                        return new Response(JSON.stringify({
                            success: false,
                            error: 'Input blocked by security system',
                            threat_level: defenseResult.threat_level
                        }), {
                            status: 403,
                            headers: { 'Content-Type': 'application/json' }
                        });
                    }
                    
                    // Sanitize prompt
                    if (body.prompt) {
                        body.prompt = swXPSystem.defenseSystem.sanitizeInput(body.prompt);
                    }
                    
                    // Track action
                    swXPSystem.trackAction(userId, 'generate_video', {
                        prompt_length: body.prompt?.length || 0,
                        timestamp: new Date().toISOString()
                    });
                    
                    // Get optimization recommendations
                    const recommendations = swXPSystem.getGenerationRecommendations(userId);
                    
                    // Add recommendations to request
                    body.optimization_hints = recommendations;
                    
                    // Create new request with sanitized body
                    const newRequest = new Request(event.request.url, {
                        method: event.request.method,
                        headers: event.request.headers,
                        body: JSON.stringify(body)
                    });
                    
                    // Forward request
                    const response = await fetch(newRequest);
                    
                    // Track completion
                    if (response.ok) {
                        const responseData = await response.clone().json().catch(() => ({}));
                        if (responseData.success) {
                            swXPSystem.trackAction(userId, 'complete_generation', {
                                documentary_id: responseData.documentary_id
                            });
                        }
                    }
                    
                    return response;
                } catch (error) {
                    console.error('[SW-XP] Error processing request:', error);
                    return fetch(event.request);
                }
            })()
        );
    } else {
        // Normal fetch for other requests
        event.respondWith(fetch(event.request));
    }
});

// Helper to get user ID
self.getUserId = function() {
    // Try to get from IndexedDB or generate persistent ID
    return 'user_' + (localStorage.getItem('user_id') || 
        (() => {
            const id = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('user_id', id);
            return id;
        })());
};

// Message handler for XP system communication
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'TRACK_ACTION') {
        const { userId, actionType, metadata } = event.data;
        const xp = swXPSystem.trackAction(userId, actionType, metadata);
        event.ports[0].postMessage({ success: true, xp_awarded: xp });
    } else if (event.data && event.data.type === 'GET_PROFILE') {
        const { userId } = event.data;
        const profile = swXPSystem.getUserProfile(userId);
        event.ports[0].postMessage({ success: true, profile });
    } else if (event.data && event.data.type === 'GET_RECOMMENDATIONS') {
        const { userId } = event.data;
        const recommendations = swXPSystem.getGenerationRecommendations(userId);
        event.ports[0].postMessage({ success: true, recommendations });
    }
});

console.log('[SW-XP] Service Worker XP System initialized');

