/**
 * Comprehensive Auto-Save System
 * Auto-saves all user data, progress, points, energy, and state
 */

class ComprehensiveAutoSave {
    constructor() {
        this.baseURL = '/api/auto-save';
        this.userId = this.getUserId();
        this.autoSaveIntervals = {
            'points': 5000,  // 5 seconds
            'energy': 10000,  // 10 seconds
            'progress': 15000,  // 15 seconds
            'state': 30000,  // 30 seconds
            'full': 60000  // 60 seconds
        };
        this.intervals = {};
        this.isEnabled = true;
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        return 'default_user';
    }

    /**
     * Start auto-save for all data types
     */
    startAutoSave() {
        if (!this.isEnabled) return;

        // Auto-save points
        this.intervals.points = setInterval(() => {
            this.autoSavePoints();
        }, this.autoSaveIntervals.points);

        // Auto-save energy
        this.intervals.energy = setInterval(() => {
            this.autoSaveEnergy();
        }, this.autoSaveIntervals.energy);

        // Auto-save progress
        this.intervals.progress = setInterval(() => {
            this.autoSaveProgress();
        }, this.autoSaveIntervals.progress);

        // Auto-save state
        this.intervals.state = setInterval(() => {
            this.autoSaveState();
        }, this.autoSaveIntervals.state);

        // Auto-save full snapshot
        this.intervals.full = setInterval(() => {
            this.autoSaveFull();
        }, this.autoSaveIntervals.full);

        console.log('[AutoSave] Auto-save started for all data types');
    }

    /**
     * Stop auto-save
     */
    stopAutoSave() {
        Object.values(this.intervals).forEach(interval => {
            if (interval) clearInterval(interval);
        });
        this.intervals = {};
        console.log('[AutoSave] Auto-save stopped');
    }

    /**
     * Auto-save points
     */
    async autoSavePoints() {
        try {
            if (window.comprehensiveAPI) {
                const points = await window.comprehensiveAPI.getPointsJSON();
                if (points.success) {
                    const response = await fetch(`${this.baseURL}/points`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user_id: this.userId,
                            points: points.points
                        })
                    });
                    const result = await response.json();
                    if (result.success) {
                        console.log('[AutoSave] Points saved');
                    }
                }
            }
        } catch (error) {
            console.error('[AutoSave] Error saving points:', error);
        }
    }

    /**
     * Auto-save energy
     */
    async autoSaveEnergy() {
        try {
            if (window.comprehensiveAPI) {
                const energy = await window.comprehensiveAPI.getEnergyStatus();
                if (energy.success) {
                    const response = await fetch(`${this.baseURL}/energy`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user_id: this.userId,
                            energy: energy
                        })
                    });
                    const result = await response.json();
                    if (result.success) {
                        console.log('[AutoSave] Energy saved');
                    }
                }
            }
        } catch (error) {
            console.error('[AutoSave] Error saving energy:', error);
        }
    }

    /**
     * Auto-save progress
     */
    async autoSaveProgress() {
        try {
            if (window.GameMechanicsAPI) {
                const progress = await window.GameMechanicsAPI.getProgress(this.userId);
                if (progress.success) {
                    const response = await fetch(`${this.baseURL}/progress`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user_id: this.userId,
                            progress: progress
                        })
                    });
                    const result = await response.json();
                    if (result.success) {
                        console.log('[AutoSave] Progress saved');
                    }
                }
            }
        } catch (error) {
            console.error('[AutoSave] Error saving progress:', error);
        }
    }

    /**
     * Auto-save state
     */
    async autoSaveState() {
        try {
            const state = {
                user_id: this.userId,
                timestamp: new Date().toISOString(),
                page: window.location.pathname,
                data: {
                    // Add any page-specific state here
                }
            };

            const response = await fetch(`${this.baseURL}/state`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    state: state
                })
            });
            const result = await response.json();
            if (result.success) {
                console.log('[AutoSave] State saved');
            }
        } catch (error) {
            console.error('[AutoSave] Error saving state:', error);
        }
    }

    /**
     * Auto-save full snapshot
     */
    async autoSaveFull() {
        try {
            // Collect all data
            const allData = {
                points: null,
                energy: null,
                progress: null,
                timestamp: new Date().toISOString()
            };

            if (window.comprehensiveAPI) {
                allData.points = await window.comprehensiveAPI.getPointsJSON();
                allData.energy = await window.comprehensiveAPI.getEnergyStatus();
            }

            if (window.GameMechanicsAPI) {
                allData.progress = await window.GameMechanicsAPI.getProgress(this.userId);
            }

            const response = await fetch(`${this.baseURL}/full`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    all_data: allData
                })
            });
            const result = await response.json();
            if (result.success) {
                console.log('[AutoSave] Full snapshot saved');
            }
        } catch (error) {
            console.error('[AutoSave] Error saving full snapshot:', error);
        }
    }

    /**
     * Get auto-save status
     */
    async getStatus() {
        try {
            const response = await fetch(`${this.baseURL}/status?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }
}

// Global instance
window.comprehensiveAutoSave = new ComprehensiveAutoSave();

// Start auto-save on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.comprehensiveAutoSave.startAutoSave();
    });
} else {
    window.comprehensiveAutoSave.startAutoSave();
}

