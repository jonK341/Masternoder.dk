/**
 * Point System Save Manager
 * Ensures all points are saved to DB and local JSON files
 * Connects all UI counters and saves them
 */
class PointSystemSaveManager {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.saveInterval = null;
        this.errorHandlers = [];
        this.eventListeners = [];
        this.lastSaveTime = null;
        this.pendingSaves = new Map();
        
        this.init();
    }
    
    init() {
        // Initialize save manager
        this.setupAutoSave();
        this.setupErrorHandlers();
        this.setupEventListeners();
        this.setupDOMWatchers();
        
        // Save on page unload
        window.addEventListener('beforeunload', () => this.emergencySave());
        
        // Save on visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.saveAllPoints();
            }
        });
    }
    
    setupAutoSave() {
        // Auto-save every 30 seconds
        this.saveInterval = setInterval(() => {
            this.saveAllPoints();
        }, 30000);
    }
    
    setupErrorHandlers() {
        const source = 'point-system-save-manager.js';
        // Global error handler
        window.addEventListener('error', (event) => {
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(event.error || new Error('Unknown error'), { source, context: 'global_error' });
            } else {
                console.error('[PointSystem] Error detected:', event.error);
            }
            this.handleError(event.error);
        });
        
        // Unhandled promise rejection
        window.addEventListener('unhandledrejection', (event) => {
            const reason = event.reason;
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(reason instanceof Error ? reason : new Error(String(reason)), { source, context: 'unhandled_rejection' });
            } else {
                console.error('[PointSystem] Unhandled rejection:', reason);
            }
            this.handleError(reason);
        });
    }
    
    setupEventListeners() {
        // Listen for point updates from unified counter
        document.addEventListener('pointsUpdated', (event) => {
            this.handlePointsUpdate(event.detail);
        });
        
        // Listen for stat changes
        document.addEventListener('statChanged', (event) => {
            this.handleStatChange(event.detail);
        });
    }
    
    setupDOMWatchers() {
        // Watch for changes in point counter elements
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    this.checkForPointUpdates();
                }
            });
        });
        
        // Observe all elements with point-related classes
        const pointElements = document.querySelectorAll('[class*="point"], [class*="counter"], [id*="point"], [id*="counter"]');
        pointElements.forEach((el) => {
            observer.observe(el, {
                childList: true,
                subtree: true,
                characterData: true
            });
        });
    }
    
    async getAllPointsFromDOM() {
        const points = {};
        
        // Get all point values from DOM
        const pointSelectors = [
            '[data-point-type]',
            '[id*="point"]',
            '[class*="point"]',
            '[data-counter]'
        ];
        
        pointSelectors.forEach((selector) => {
            document.querySelectorAll(selector).forEach((el) => {
                const pointType = el.getAttribute('data-point-type') || 
                                el.id.replace(/[^a-zA-Z]/g, '') ||
                                el.className.split(' ').find(c => c.includes('point')) ||
                                'unknown';
                
                const value = this.extractNumericValue(el.textContent);
                if (value !== null && pointType !== 'unknown') {
                    points[pointType] = value;
                }
            });
        });
        
        // Get from unified counter if available
        if (window.unifiedPointCounters) {
            try {
                const unifiedPoints = await window.unifiedPointCounters.getAllPoints();
                Object.assign(points, unifiedPoints);
            } catch (e) {
                if (window.ErrorManager) {
                    window.ErrorManager.logJSError(e instanceof Error ? e : new Error(String(e)), { source: 'point-system-save-manager.js', context: 'getAllPointsFromDOM_unified' });
                } else {
                    console.error('[PointSystem] Error getting unified points:', e);
                }
            }
        }
        
        return points;
    }
    
    extractNumericValue(text) {
        if (!text) return null;
        const match = text.match(/[\d,]+/);
        if (match) {
            return parseInt(match[0].replace(/,/g, ''), 10);
        }
        return null;
    }
    
    async saveAllPoints() {
        try {
            // Get all points from DOM and unified counter
            const allPoints = await this.getAllPointsFromDOM();
            
            // Add metadata
            allPoints.last_updated = new Date().toISOString();
            allPoints.user_id = this.userId;
            
            // Save to both DB and JSON
            const [dbResult, jsonResult] = await Promise.all([
                this.saveToDatabase(allPoints),
                this.saveToLocalJSON(allPoints)
            ]);
            
            this.lastSaveTime = new Date().toISOString();
            
            // Verify save
            if (!dbResult.success || !jsonResult.success) {
                if (window.ErrorManager) {
                    window.ErrorManager.logJSError(new Error('Save failed'), { source: 'point-system-save-manager.js', context: 'saveAllPoints_verify', dbResult, jsonResult });
                } else {
                    console.error('[PointSystem] Save failed:', { dbResult, jsonResult });
                }
                this.handleSaveError({ dbResult, jsonResult });
            } else {
                console.log('[PointSystem] All points saved successfully');
            }
            
            return {
                success: dbResult.success && jsonResult.success,
                dbResult,
                jsonResult,
                points: allPoints
            };
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(error, { source: 'point-system-save-manager.js', context: 'saveAllPoints' });
            } else {
                console.error('[PointSystem] Error saving points:', error);
            }
            this.handleError(error);
            return { success: false, error: error.message };
        }
    }
    
    async saveToDatabase(points) {
        try {
            const response = await fetch('/api/point-system-repair/save-all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    points_data: points
                })
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logNetworkError('/api/point-system-repair/save-all', 'POST', error.message);
            } else {
                console.error('[PointSystem] Database save error:', error);
            }
            return { success: false, error: error.message };
        }
    }
    
    async saveToLocalJSON(points) {
        try {
            const fileName = `${this.userId}_points.json`;
            // Only show folder/file picker once per 24h (sessionStorage)
            const keySaveAsked = 'point_system_save_file_asked_at';
            const cooldownMs = 24 * 60 * 60 * 1000;
            let mayShowPicker = true;
            try {
                const askedAt = sessionStorage.getItem(keySaveAsked);
                if (askedAt && (Date.now() - parseInt(askedAt, 10)) < cooldownMs) mayShowPicker = false;
            } catch (_) {}

            if (mayShowPicker && 'showSaveFilePicker' in window) {
                try {
                    const fileHandle = await window.showSaveFilePicker({
                        suggestedName: fileName,
                        types: [{ description: 'JSON files', accept: { 'application/json': ['.json'] } }]
                    });
                    const writable = await fileHandle.createWritable();
                    await writable.write(JSON.stringify(points, null, 2));
                    await writable.close();
                    try { sessionStorage.setItem(keySaveAsked, String(Date.now())); } catch (_) {}
                    return { success: true, file_path: fileHandle.name };
                } catch (e) {
                    try { sessionStorage.setItem(keySaveAsked, String(Date.now())); } catch (_) {}
                }
            }
            // No picker shown (cooldown or cancelled): save to localStorage only
            localStorage.setItem(`points_${this.userId}`, JSON.stringify(points));
            return { success: true, method: 'localStorage' };
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(error, { source: 'point-system-save-manager.js', context: 'saveToLocalJSON' });
            } else {
                console.error('[PointSystem] JSON save error:', error);
            }
            // Fallback: Save to localStorage
            try {
                localStorage.setItem(`points_${this.userId}`, JSON.stringify(points));
                return { success: true, method: 'localStorage' };
            } catch (e) {
                return { success: false, error: e.message };
            }
        }
    }
    
    async getUserDataDirectory() {
        // Only show folder picker once per session (timer: 24h in sessionStorage)
        const keyAsked = 'point_system_dir_asked_at';
        const keyDeclined = 'point_system_dir_declined';
        const cooldownMs = 24 * 60 * 60 * 1000;
        try {
            if (sessionStorage.getItem(keyDeclined)) return null;
            const askedAt = sessionStorage.getItem(keyAsked);
            if (askedAt && (Date.now() - parseInt(askedAt, 10)) < cooldownMs) return null;
            if (this._cachedDirHandle) return this._cachedDirHandle;
        } catch (_) {}
        if ('showDirectoryPicker' in window) {
            try {
                const dirHandle = await window.showDirectoryPicker();
                this._cachedDirHandle = dirHandle;
                try { sessionStorage.setItem(keyAsked, String(Date.now())); } catch (_) {}
                return dirHandle;
            } catch (e) {
                try { sessionStorage.setItem(keyDeclined, '1'); } catch (_) {}
            }
        }
        return null;
    }
    
    async emergencySave() {
        // Emergency save before page unload
        try {
            const points = await this.getAllPointsFromDOM();
            await this.saveToLocalJSON(points);
            // Try to save to DB (fire and forget)
            this.saveToDatabase(points).catch(() => {});
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(error, { source: 'point-system-save-manager.js', context: 'emergencySave' });
            } else {
                console.error('[PointSystem] Emergency save error:', error);
            }
        }
    }
    
    handlePointsUpdate(detail) {
        // Handle points update event
        const { pointType, value } = detail;
        this.pendingSaves.set(pointType, value);
        
        // Debounced save
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            this.saveAllPoints();
        }, 2000);
    }
    
    handleStatChange(detail) {
        // Handle stat change event
        const { statName, statValue } = detail;
        this.pendingSaves.set(statName, statValue);
        
        // Trigger progression save
        this.triggerProgressionSave(statName, statValue);
    }
    
    async triggerProgressionSave(statName, statValue) {
        try {
            const response = await fetch('/api/point-system-repair/trigger-progression', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    stat_name: statName,
                    stat_value: statValue
                })
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logNetworkError('/api/point-system-repair/trigger-progression', 'POST', error.message);
            } else {
                console.error('[PointSystem] Progression save error:', error);
            }
            return { success: false, error: error.message };
        }
    }
    
    checkForPointUpdates() {
        // Check DOM for point updates
        this.getAllPointsFromDOM().then((points) => {
            if (Object.keys(points).length > 0) {
                this.pendingSaves.clear();
                Object.entries(points).forEach(([key, value]) => {
                    this.pendingSaves.set(key, value);
                });
            }
        });
    }
    
    handleError(error) {
        if (window.ErrorManager) {
            window.ErrorManager.logJSError(error instanceof Error ? error : new Error(String(error)), { source: 'point-system-save-manager.js', context: 'handleError' });
        } else {
            console.error('[PointSystem] Error:', error);
        }
        
        // Try to save current state
        this.emergencySave();
        
        // Notify user if critical
        if (error && error.message && error.message.includes('point')) {
            if (window.ErrorManager) {
                window.ErrorManager.logJSError(new Error('Point-related error detected, attempting recovery'), { source: 'point-system-save-manager.js', context: 'handleError_point_recovery' });
            } else {
                console.warn('[PointSystem] Point-related error detected, attempting recovery...');
            }
        }
    }
    
    handleSaveError(errorData) {
        if (window.ErrorManager) {
            window.ErrorManager.logJSError(new Error('Save error'), { source: 'point-system-save-manager.js', context: 'handleSaveError', save_error: errorData });
        } else {
            console.error('[PointSystem] Save error:', errorData);
        }
        
        // Retry save
        setTimeout(() => {
            this.saveAllPoints();
        }, 5000);
    }
    
    async repairLostCounters() {
        try {
            const response = await fetch(`/api/point-system-repair/repair/${this.userId}`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success && result.recovered_points) {
                // Update DOM with recovered points
                this.updateDOMWithPoints(result.recovered_points);
            }
            
            return result;
        } catch (error) {
            if (window.ErrorManager) {
                window.ErrorManager.logNetworkError(`/api/point-system-repair/repair/${this.userId}`, 'POST', error.message);
            } else {
                console.error('[PointSystem] Repair error:', error);
            }
            return { success: false, error: error.message };
        }
    }
    
    updateDOMWithPoints(points) {
        // Update DOM elements with recovered points
        Object.entries(points).forEach(([pointType, value]) => {
            const elements = document.querySelectorAll(`[data-point-type="${pointType}"]`);
            elements.forEach((el) => {
                el.textContent = value.toLocaleString();
            });
        });
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pointSystemSaveManager = new PointSystemSaveManager();
    });
} else {
    window.pointSystemSaveManager = new PointSystemSaveManager();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PointSystemSaveManager;
}

