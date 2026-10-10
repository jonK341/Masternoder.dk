/**
 * XP System Integration for Generator Page
 * Connects generator to XP system and service worker
 */

(function() {
    'use strict';
    
    // XP System Client
    class XPClient {
        constructor() {
            this.userId = this.getUserId();
            this.serviceWorkerReady = false;
            this.initServiceWorker();
        }
        
        getUserId() {
            // Get or create user ID
            let userId = localStorage.getItem('user_id');
            if (!userId) {
                userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('user_id', userId);
            }
            return userId;
        }
        
        async initServiceWorker() {
            if ('serviceWorker' in navigator) {
                try {
                    const registration = await navigator.serviceWorker.register('/vidgenerator/static/js/service-worker-xp.js');
                    this.serviceWorkerReady = true;
                    console.log('[XP] Service worker registered');
                } catch (e) {
                    console.warn('[XP] Service worker registration failed:', e);
                }
            }
        }
        
        async trackAction(actionType, metadata = {}) {
            if (!this.serviceWorkerReady) {
                // Fallback: track locally
                this.trackLocal(actionType, metadata);
                return;
            }
            
            try {
                const messageChannel = new MessageChannel();
                return new Promise((resolve) => {
                    messageChannel.port1.onmessage = (event) => {
                        if (event.data.success) {
                            console.log(`[XP] Action tracked: ${actionType}, +${event.data.xp_awarded} XP`);
                            resolve(event.data);
                        }
                    };
                    
                    navigator.serviceWorker.controller.postMessage({
                        type: 'TRACK_ACTION',
                        userId: this.userId,
                        actionType: actionType,
                        metadata: metadata
                    }, [messageChannel.port2]);
                });
            } catch (e) {
                console.warn('[XP] Track action error:', e);
                this.trackLocal(actionType, metadata);
            }
        }
        
        trackLocal(actionType, metadata) {
            // Local fallback tracking
            const xpData = JSON.parse(localStorage.getItem('xp_data') || '{}');
            if (!xpData[this.userId]) {
                xpData[this.userId] = { total_xp: 0, actions: {} };
            }
            
            const xpValues = {
                'generate_video': 100,
                'watch_video': 10,
                'complete_generation': 50
            };
            
            const xp = xpValues[actionType] || 5;
            xpData[this.userId].total_xp += xp;
            xpData[this.userId].actions[actionType] = (xpData[this.userId].actions[actionType] || 0) + 1;
            
            localStorage.setItem('xp_data', JSON.stringify(xpData));
            console.log(`[XP] Local tracking: ${actionType}, +${xp} XP`);
        }
        
        async getUserProfile() {
            if (!this.serviceWorkerReady) {
                return this.getLocalProfile();
            }
            
            try {
                const messageChannel = new MessageChannel();
                return new Promise((resolve) => {
                    messageChannel.port1.onmessage = (event) => {
                        if (event.data.success) {
                            resolve(event.data.profile);
                        }
                    };
                    
                    navigator.serviceWorker.controller.postMessage({
                        type: 'GET_PROFILE',
                        userId: this.userId
                    }, [messageChannel.port2]);
                });
            } catch (e) {
                console.warn('[XP] Get profile error:', e);
                return this.getLocalProfile();
            }
        }
        
        getLocalProfile() {
            const xpData = JSON.parse(localStorage.getItem('xp_data') || '{}');
            const userData = xpData[this.userId] || { total_xp: 0, actions: {} };
            return {
                behavioral: {
                    total_xp: userData.total_xp,
                    level: Math.floor(userData.total_xp / 1000) + 1,
                    actions: userData.actions
                }
            };
        }
        
        async getRecommendations() {
            if (!this.serviceWorkerReady) {
                return this.getLocalRecommendations();
            }
            
            try {
                const messageChannel = new MessageChannel();
                return new Promise((resolve) => {
                    messageChannel.port1.onmessage = (event) => {
                        if (event.data.success) {
                            resolve(event.data.recommendations);
                        }
                    };
                    
                    navigator.serviceWorker.controller.postMessage({
                        type: 'GET_RECOMMENDATIONS',
                        userId: this.userId
                    }, [messageChannel.port2]);
                });
            } catch (e) {
                console.warn('[XP] Get recommendations error:', e);
                return this.getLocalRecommendations();
            }
        }
        
        getLocalRecommendations() {
            return {
                clip_duration_range: [5, 15],
                target_duration_range: [180, 600],
                optimization_priority: 'balanced'
            };
        }
    }
    
    // Initialize XP Client
    const xpClient = new XPClient();
    window.xpClient = xpClient;
    
    // Track page load
    document.addEventListener('DOMContentLoaded', function() {
        xpClient.trackAction('return_user', {
            page: 'generator',
            timestamp: new Date().toISOString()
        });
        
        // Display user level if available
        xpClient.getUserProfile().then(profile => {
            const level = profile.behavioral?.level || 1;
            const xp = profile.behavioral?.total_xp || 0;
            console.log(`[XP] User Level: ${level}, Total XP: ${xp}`);
            
            // Optionally display in UI
            const levelDisplay = document.getElementById('user-level-display');
            if (levelDisplay) {
                levelDisplay.textContent = `Level ${level} (${xp} XP)`;
            }
        });
    });
    
    // Track generation start
    if (typeof window !== 'undefined' && window.addEventListener) {
        window.addEventListener('generationStarted', function(event) {
            xpClient.trackAction('generate_video', {
                prompt: event.detail?.prompt?.substring(0, 100) || '',
                timestamp: new Date().toISOString()
            });
        });
        
        // Track generation completion
        window.addEventListener('generationCompleted', function(event) {
            xpClient.trackAction('complete_generation', {
                documentary_id: event.detail?.documentary_id || '',
                timestamp: new Date().toISOString()
            });
        });
    }
    
    console.log('[XP] XP System Client initialized');
})();

