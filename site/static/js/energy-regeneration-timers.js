/**
 * Energy Regeneration Timers
 * Automatic energy regeneration over time with visual timers
 */
class EnergyRegenerationTimers {
    constructor() {
        this.baseURL = '/api/ultra-resource';
        this.userId = this.getUserId();
        this.regenerationRates = {
            'mind': 1.0,      // 1 point per minute
            'power': 0.8,     // 0.8 points per minute
            'time': 0.5,      // 0.5 points per minute
            'place': 0.3      // 0.3 points per minute
        };
        this.maxCapacity = {
            'mind': 100,
            'power': 100,
            'time': 100,
            'place': 100
        };
        this.timers = {};
        this.lastUpdate = {};
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        return 'default_user';
    }

    /**
     * Initialize energy regeneration
     */
    async init() {
        await this.loadEnergy();
        this.startRegeneration();
        this.updateDisplay();
        
        // Update display every second
        setInterval(() => this.updateDisplay(), 1000);
        
        // Save energy every 30 seconds
        setInterval(() => this.saveEnergy(), 30000);
    }

    /**
     * Load current energy
     */
    async loadEnergy() {
        try {
            const response = await fetch(`${this.baseURL}/energy?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success && data.energy) {
                for (const [type, value] of Object.entries(data.energy)) {
                    if (type !== 'last_update' && this.regenerationRates[type]) {
                        this.timers[type] = {
                            current: value,
                            max: this.maxCapacity[type],
                            lastUpdate: data.energy.last_update ? new Date(data.energy.last_update) : new Date()
                        };
                    }
                }
            }
        } catch (error) {
            console.error('Error loading energy:', error);
        }
    }

    /**
     * Start regeneration process
     */
    startRegeneration() {
        // Calculate regeneration based on time passed
        const now = new Date();
        
        for (const [type, timer] of Object.entries(this.timers)) {
            if (!timer) continue;
            
            const timePassed = (now - timer.lastUpdate) / 1000 / 60; // minutes
            const regeneration = timePassed * this.regenerationRates[type];
            
            if (regeneration > 0) {
                timer.current = Math.min(timer.max, timer.current + regeneration);
                timer.lastUpdate = now;
            }
        }
    }

    /**
     * Update display
     */
    updateDisplay() {
        const now = new Date();
        
        for (const [type, timer] of Object.entries(this.timers)) {
            if (!timer) continue;
            
            // Calculate regeneration since last update
            const timePassed = (now - timer.lastUpdate) / 1000 / 60; // minutes
            const regeneration = timePassed * this.regenerationRates[type];
            
            if (regeneration > 0.01) { // Only update if significant
                timer.current = Math.min(timer.max, timer.current + regeneration);
                timer.lastUpdate = now;
            }
            
            // Update UI elements
            this.updateEnergyBar(type, timer.current, timer.max);
            this.updateTimerDisplay(type, timer);
        }
    }

    /**
     * Update energy bar
     */
    updateEnergyBar(type, current, max) {
        const bar = document.getElementById(`energy-${type}-bar`);
        const fill = document.getElementById(`energy-${type}-fill`);
        const text = document.getElementById(`energy-${type}-text`);
        
        if (bar && fill) {
            const percentage = (current / max) * 100;
            fill.style.width = `${percentage}%`;
            
            if (text) {
                text.textContent = `${current.toFixed(1)}/${max}`;
            }
        }
    }

    /**
     * Update timer display
     */
    updateTimerDisplay(type, timer) {
        const timerEl = document.getElementById(`energy-${type}-timer`);
        if (!timerEl) return;
        
        const remaining = timer.max - timer.current;
        const rate = this.regenerationRates[type];
        const minutesToFull = remaining / rate;
        
        if (minutesToFull > 0 && minutesToFull < 1000) {
            if (minutesToFull < 1) {
                timerEl.textContent = `${Math.floor(minutesToFull * 60)}s to full`;
            } else if (minutesToFull < 60) {
                timerEl.textContent = `${Math.floor(minutesToFull)}m to full`;
            } else {
                timerEl.textContent = `${Math.floor(minutesToFull / 60)}h to full`;
            }
        } else {
            timerEl.textContent = 'Full';
        }
    }

    /**
     * Save energy to server
     */
    async saveEnergy() {
        try {
            const energy = {};
            for (const [type, timer] of Object.entries(this.timers)) {
                if (timer) {
                    energy[type] = timer.current;
                }
            }
            energy.last_update = new Date().toISOString();
            
            const response = await fetch(`${this.baseURL}/energy`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    energy: energy
                })
            });
            
            if (response.ok) {
                console.log('[EnergyRegen] Energy saved');
            }
        } catch (error) {
            console.error('[EnergyRegen] Error saving energy:', error);
        }
    }

    /**
     * Add energy boost
     */
    async addEnergyBoost(type, amount) {
        if (!this.timers[type]) return;
        
        this.timers[type].current = Math.min(
            this.timers[type].max,
            this.timers[type].current + amount
        );
        
        this.updateDisplay();
        await this.saveEnergy();
    }
}

// Global instance
const energyRegenerationTimers = new EnergyRegenerationTimers();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        energyRegenerationTimers.init();
    });
} else {
    energyRegenerationTimers.init();
}

