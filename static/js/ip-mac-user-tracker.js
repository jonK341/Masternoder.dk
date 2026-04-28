/**
 * IP/MAC User Tracker
 * Client-side script to capture and send MAC address to server
 * Note: MAC addresses are not directly accessible via JavaScript for security reasons
 * This script attempts to get device fingerprint and sends it to server
 */
(function() {
    'use strict';
    
    class IPMACUserTracker {
        constructor() {
            this.baseURL = '/api';
            this.deviceFingerprint = null;
            this.macAddress = null;
        }
        
        /**
         * Generate device fingerprint (since MAC is not accessible)
         * Combines multiple browser/device characteristics
         */
        generateDeviceFingerprint() {
            if (this.deviceFingerprint) {
                return this.deviceFingerprint;
            }
            
            const components = [];
            
            // Screen properties
            components.push(`screen:${screen.width}x${screen.height}`);
            components.push(`colorDepth:${screen.colorDepth}`);
            components.push(`pixelDepth:${screen.pixelDepth}`);
            
            // Browser properties
            components.push(`userAgent:${navigator.userAgent}`);
            components.push(`language:${navigator.language}`);
            components.push(`platform:${navigator.platform}`);
            components.push(`hardwareConcurrency:${navigator.hardwareConcurrency || 'unknown'}`);
            components.push(`maxTouchPoints:${navigator.maxTouchPoints || 0}`);
            
            // Timezone
            components.push(`timezone:${Intl.DateTimeFormat().resolvedOptions().timeZone}`);
            
            // Canvas fingerprint
            try {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillText('Device fingerprint', 2, 2);
                components.push(`canvas:${canvas.toDataURL().substring(0, 50)}`);
            } catch (e) {
                components.push('canvas:error');
            }
            
            // WebGL fingerprint
            try {
                const gl = document.createElement('canvas').getContext('webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    if (debugInfo) {
                        components.push(`webglVendor:${gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)}`);
                        components.push(`webglRenderer:${gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)}`);
                    }
                }
            } catch (e) {
                components.push('webgl:error');
            }
            
            // Audio fingerprint
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const analyser = audioContext.createAnalyser();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(analyser);
                analyser.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.value = 10000;
                gainNode.gain.value = 0;
                
                const audioFingerprint = analyser.frequencyBinCount;
                components.push(`audio:${audioFingerprint}`);
                
                audioContext.close();
            } catch (e) {
                components.push('audio:error');
            }
            
            // Combine all components
            const fingerprint = components.join('|');
            
            // Create hash-like identifier
            let hash = 0;
            for (let i = 0; i < fingerprint.length; i++) {
                const char = fingerprint.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash; // Convert to 32-bit integer
            }
            
            this.deviceFingerprint = `fp_${Math.abs(hash).toString(16)}`;
            return this.deviceFingerprint;
        }
        
        /**
         * Try to get MAC address via WebRTC (limited support)
         * Note: This is not reliable and may not work in all browsers
         */
        async tryGetMACAddress() {
            // MAC addresses are not accessible via standard web APIs
            // This is a placeholder for future implementations
            // Some browsers may expose MAC via WebRTC, but it's not standard
            
            // For now, use device fingerprint as MAC-like identifier
            const fingerprint = this.generateDeviceFingerprint();
            this.macAddress = fingerprint;
            
            return this.macAddress;
        }
        
        /**
         * Register device with server
         */
        async registerDevice() {
            try {
                // Get device fingerprint (MAC-like identifier)
                const macAddress = await this.tryGetMACAddress();
                
                // Send to server
                const response = await fetch(`${this.baseURL}/user/register-mac`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        mac_address: macAddress,
                        device_fingerprint: this.deviceFingerprint,
                        timestamp: new Date().toISOString()
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('[IPMACUserTracker] Device registered:', data.user_id);
                    // Store user ID in localStorage
                    if (data.user_id) {
                        localStorage.setItem('user_id', data.user_id);
                    }
                }
                
                return data;
            } catch (error) {
                console.error('[IPMACUserTracker] Error registering device:', error);
                return { success: false, error: error.message };
            }
        }
        
        /**
         * Get current user from server
         */
        async getCurrentUser() {
            try {
                const response = await fetch(`${this.baseURL}/user/current`);
                const data = await response.json();
                
                if (data.success && data.user_id) {
                    localStorage.setItem('user_id', data.user_id);
                    return data;
                }
                
                return data;
            } catch (error) {
                console.error('[IPMACUserTracker] Error getting current user:', error);
                return { success: false, error: error.message };
            }
        }
        
        /**
         * Initialize tracker
         */
        init() {
            // Generate fingerprint immediately
            this.generateDeviceFingerprint();
            
            // Register device on page load
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    this.registerDevice();
                    this.getCurrentUser();
                });
            } else {
                this.registerDevice();
                this.getCurrentUser();
            }
            
            // Re-register on visibility change (user returns to tab)
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    this.registerDevice();
                }
            });
        }
    }
    
    // Initialize tracker
    const tracker = new IPMACUserTracker();
    tracker.init();
    
    // Make available globally
    window.IPMACUserTracker = tracker;
    
})();
