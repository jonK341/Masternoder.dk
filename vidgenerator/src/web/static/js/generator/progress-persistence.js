/**
 * Progress Persistence
 * Saves and restores generation progress across page refreshes
 */

class ProgressPersistence {
    constructor() {
        this.storageKey = 'generator_progress';
        this.maxAge = 24 * 60 * 60 * 1000; // 24 hours
    }
    
    /**
     * Save generation progress
     */
    saveProgress(progressData) {
        try {
            const data = {
                ...progressData,
                timestamp: Date.now(),
                savedAt: new Date().toISOString()
            };
            
            localStorage.setItem(this.storageKey, JSON.stringify(data));
            console.log('[ProgressPersistence] Progress saved:', data);
            return true;
        } catch (error) {
            console.error('[ProgressPersistence] Failed to save progress:', error);
            return false;
        }
    }
    
    /**
     * Load saved progress
     */
    loadProgress() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (!stored) {
                return null;
            }
            
            const data = JSON.parse(stored);
            
            // Check if data is too old
            const age = Date.now() - data.timestamp;
            if (age > this.maxAge) {
                console.log('[ProgressPersistence] Progress too old, clearing');
                this.clearProgress();
                return null;
            }
            
            console.log('[ProgressPersistence] Progress loaded:', data);
            return data;
        } catch (error) {
            console.error('[ProgressPersistence] Failed to load progress:', error);
            this.clearProgress();
            return null;
        }
    }
    
    /**
     * Clear saved progress
     */
    clearProgress() {
        try {
            localStorage.removeItem(this.storageKey);
            console.log('[ProgressPersistence] Progress cleared');
            return true;
        } catch (error) {
            console.error('[ProgressPersistence] Failed to clear progress:', error);
            return false;
        }
    }
    
    /**
     * Update progress (merge with existing)
     */
    updateProgress(updates) {
        const existing = this.loadProgress();
        if (existing) {
            return this.saveProgress({ ...existing, ...updates });
        }
        return this.saveProgress(updates);
    }
    
    /**
     * Check if there's saved progress
     */
    hasProgress() {
        const progress = this.loadProgress();
        return progress !== null;
    }
    
    /**
     * Get progress age in minutes
     */
    getProgressAge() {
        const progress = this.loadProgress();
        if (!progress) {
            return null;
        }
        
        const age = Date.now() - progress.timestamp;
        return Math.floor(age / 60000); // Convert to minutes
    }
}

// Global instance
const progressPersistence = new ProgressPersistence();

// Make available globally
if (typeof window !== 'undefined') {
    window.progressPersistence = progressPersistence;
    window.ProgressPersistence = ProgressPersistence;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressPersistence;
}

