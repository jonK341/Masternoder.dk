/**
 * Point System Repair - Frontend
 * Saves all points to DB and local JSON, adds triggers, event listeners
 */
class PointSystemRepair {
    constructor() {
        this.baseUrl = window.location.origin;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.pointsCache = {};
        this.saveInterval = null;
        this.eventListeners = {};
        
        this.init();
    }
    
    init() {
        // Load points from local storage
        this.loadPointsFromLocal();
        
        // Set up auto-save
        this.setupAutoSave();
        
        // Set up error handlers
        this.setupErrorHandlers();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Set up progression triggers
        this.setupProgressionTriggers();
    }
    
    loadPointsFromLocal() {
        try {
            const saved = localStorage.getItem('masternoder_points');
            if (saved) {
                this.pointsCache = JSON.parse(saved);
                console.log('[PointSystemRepair] Loaded points from local storage', this.pointsCache);
            }
        } catch (e) {
            console.error('[PointSystemRepair] Error loading points:', e);
        }
    }
    
    savePointsToLocal(points) {
        try {
            const data = {
                user_id: this.userId,
                points: points,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem('masternoder_points', JSON.stringify(data));
            console.log('[PointSystemRepair] Saved points to local storage');
        } catch (e) {
            console.error('[PointSystemRepair] Error saving to local:', e);
        }
    }
    
    async savePointsToDB(points) {
        try {
            const response = await fetch(`${this.baseUrl}/api/point-repair/save-to-db`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    points: points
                })
            });
            
            const result = await response.json();
            if (result.success) {
                console.log('[PointSystemRepair] Saved points to DB');
            }
            return result;
        } catch (e) {
            console.error('[PointSystemRepair] Error saving to DB:', e);
            return { success: false, error: e.message };
        }
    }
    
    async savePointsToLocalJSON(points) {
        try {
            const response = await fetch(`${this.baseUrl}/api/point-repair/save-to-local`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    points: points
                })
            });
            
            const result = await response.json();
            return result;
        } catch (e) {
            console.error('[PointSystemRepair] Error saving to local JSON:', e);
            return { success: false, error: e.message };
        }
    }
    
    async saveAllPoints(points) {
        // Update cache
        this.pointsCache = { ...this.pointsCache, ...points };
        
        // Save to local storage
        this.savePointsToLocal(this.pointsCache);
        
        // Save to DB
        await this.savePointsToDB(this.pointsCache);
        
        // Save to local JSON file
        await this.savePointsToLocalJSON(this.pointsCache);
        
        // Trigger event
        this.triggerEvent('points_saved', { points: this.pointsCache });
    }
    
    setupAutoSave() {
        // Auto-save every 30 seconds
        this.saveInterval = setInterval(() => {
            if (Object.keys(this.pointsCache).length > 0) {
                this.saveAllPoints(this.pointsCache);
            }
        }, 30000);
        
        // Save on page unload
        window.addEventListener('beforeunload', () => {
            if (Object.keys(this.pointsCache).length > 0) {
                // Use sendBeacon for reliable save on unload
                navigator.sendBeacon(
                    `${this.baseUrl}/api/point-repair/save-to-db`,
                    JSON.stringify({
                        user_id: this.userId,
                        points: this.pointsCache
                    })
                );
            }
        });
    }
    
    setupErrorHandlers() {
        // Global error handler
        window.addEventListener('error', (event) => {
            console.error('[PointSystemRepair] Global error:', event.error);
            this.triggerEvent('error', { error: event.error, message: event.message });
        });
        
        // Unhandled promise rejection
        window.addEventListener('unhandledrejection', (event) => {
            console.error('[PointSystemRepair] Unhandled rejection:', event.reason);
            this.triggerEvent('error', { error: event.reason, type: 'promise_rejection' });
        });
    }
    
    setupEventListeners() {
        // Listen for point updates from all systems
        document.addEventListener('pointsUpdated', (event) => {
            const points = event.detail.points || {};
            this.saveAllPoints(points);
        });
        
        // Listen for DOM counter updates
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    // Check if point counter was updated
                    const target = mutation.target;
                    if (target.classList && target.classList.contains('point-counter')) {
                        const points = this.extractPointsFromDOM();
                        if (Object.keys(points).length > 0) {
                            this.saveAllPoints(points);
                        }
                    }
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });
    }
    
    setupProgressionTriggers() {
        // Monitor all stat elements for progression
        const statElements = document.querySelectorAll('[data-stat], .stat-counter, .point-counter');
        
        statElements.forEach((element) => {
            const statName = element.dataset.stat || element.className;
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    const previousValue = parseFloat(mutation.oldValue || 0);
                    const currentValue = parseFloat(element.textContent || 0);
                    
                    if (currentValue > previousValue) {
                        this.checkProgressionTrigger(statName, currentValue, previousValue);
                    }
                });
            });
            
            observer.observe(element, {
                characterData: true,
                childList: true,
                attributes: true,
                attributeOldValue: true
            });
        });
    }
    
    async checkProgressionTrigger(statName, currentValue, previousValue) {
        try {
            const response = await fetch(`${this.baseUrl}/api/point-repair/check-progression/${this.userId}/${statName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_value: currentValue,
                    previous_value: previousValue
                })
            });
            
            const result = await response.json();
            if (result.success && result.triggered) {
                // Award bonus points
                if (result.bonus_points > 0) {
                    this.addPoints('bonus_points', result.bonus_points);
                }
                
                // Show notification
                if (typeof toast !== 'undefined') {
                    toast.success(result.message || `Milestone reached! +${result.bonus_points} bonus points`);
                }
            }
        } catch (e) {
            console.error('[PointSystemRepair] Error checking progression:', e);
        }
    }
    
    extractPointsFromDOM() {
        const points = {};
        
        // Extract from all point counter elements
        document.querySelectorAll('.point-counter, [data-point-type]').forEach((element) => {
            const pointType = element.dataset.pointType || element.className.replace('point-counter', '').trim();
            const value = parseFloat(element.textContent || 0);
            
            if (pointType && !isNaN(value)) {
                points[pointType] = value;
            }
        });
        
        return points;
    }
    
    addPoints(pointType, amount) {
        if (!this.pointsCache[pointType]) {
            this.pointsCache[pointType] = 0;
        }
        this.pointsCache[pointType] += amount;
        this.saveAllPoints({ [pointType]: this.pointsCache[pointType] });
    }
    
    triggerEvent(eventType, data) {
        const event = new CustomEvent(eventType, { detail: data });
        document.dispatchEvent(event);
    }
    
    async repairCounters() {
        try {
            const response = await fetch(`${this.baseUrl}/api/point-repair/repair-counters/${this.userId}`, {
                method: 'POST'
            });
            
            const result = await response.json();
            if (result.success) {
                // Update DOM with repaired points
                this.updateDOMWithPoints(result.points);
                this.pointsCache = result.points;
                this.saveAllPoints(result.points);
            }
            return result;
        } catch (e) {
            console.error('[PointSystemRepair] Error repairing counters:', e);
            return { success: false, error: e.message };
        }
    }
    
    updateDOMWithPoints(points) {
        Object.keys(points).forEach((pointType) => {
            const element = document.querySelector(`[data-point-type="${pointType}"]`);
            if (element) {
                element.textContent = points[pointType];
            }
        });
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pointSystemRepair = new PointSystemRepair();
    });
} else {
    window.pointSystemRepair = new PointSystemRepair();
}
