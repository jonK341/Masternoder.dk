/**
 * Progression Triggers - Client-side
 * Triggers for all stats in the point system including DOM elements
 */
class ProgressionTriggers {
    constructor() {
        this.baseUrl = window.location.origin;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.observer = null;
        this.checkInterval = null;
        this.init();
    }
    
    init() {
        // Watch DOM for counter changes
        this.setupDOMObserver();
        
        // Check progression every 10 seconds
        this.startProgressionCheck();
        
        // Check on point updates
        document.addEventListener('pointsUpdated', () => this.checkAllStats());
        
        // Initial check
        this.checkAllStats();
    }
    
    setupDOMObserver() {
        // Watch for changes in counter elements
        const targetNode = document.body;
        const config = { 
            childList: true, 
            subtree: true, 
            characterData: true,
            attributes: true,
            attributeFilter: ['data-point-type', 'data-counter']
        };
        
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    // Check if counter value changed
                    this.checkDOMCounters();
                }
            });
        });
        
        this.observer.observe(targetNode, config);
    }
    
    checkDOMCounters() {
        // Get all counter values from DOM
        const counters = this.getAllDOMCounters();
        
        // Check progression for each
        Object.keys(counters).forEach(statType => {
            this.checkProgression(statType, counters[statType]);
        });
    }
    
    getAllDOMCounters() {
        const counters = {};
        
        // Get all counter elements
        const counterElements = document.querySelectorAll(
            '[data-point-type], [data-counter], .point-counter, .stat-value, [id*="counter"], [id*="points"]'
        );
        
        counterElements.forEach(element => {
            const statType = element.getAttribute('data-point-type') || 
                            element.getAttribute('data-counter') ||
                            element.id.replace(/-counter|-value|-points/g, '') ||
                            element.className.match(/point-(\w+)|stat-(\w+)/)?.[1] || 
                            element.className.match(/point-(\w+)|stat-(\w+)/)?.[2];
            
            if (statType) {
                const value = this.parseNumber(element.textContent);
                if (value !== null) {
                    counters[statType] = value;
                }
            }
        });
        
        return counters;
    }
    
    async checkProgression(statType, currentValue) {
        try {
            const response = await fetch(`${this.baseUrl}/api/progression-triggers/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    stat_type: statType,
                    current_value: currentValue
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.progression_events && result.progression_events.length > 0) {
                // Show milestone notifications
                result.progression_events.forEach(event => {
                    this.showMilestoneNotification(event);
                });
                
                // Trigger point update
                document.dispatchEvent(new CustomEvent('pointsUpdated', {
                    detail: { progression_events: result.progression_events }
                }));
            }
        } catch (error) {
            console.error('[ProgressionTriggers] Error checking progression:', error);
        }
    }
    
    async checkAllStats() {
        try {
            const response = await fetch(`${this.baseUrl}/api/progression-triggers/check-all/${this.userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (result.success && result.events && result.events.length > 0) {
                result.events.forEach(event => {
                    this.showMilestoneNotification(event);
                });
            }
        } catch (error) {
            console.error('[ProgressionTriggers] Error checking all stats:', error);
        }
    }
    
    showMilestoneNotification(event) {
        const milestone = event.milestone;
        const statType = event.stat_type;
        const points = event.milestone_points || 0;
        
        // Show toast notification
        if (window.toast) {
            window.toast.success(
                `🎉 Milestone Reached! ${statType}: ${milestone} (+${points} points)`,
                { duration: 5000 }
            );
        }
        
        // Create visual effect
        this.createMilestoneEffect(event);
    }
    
    createMilestoneEffect(event) {
        // Create celebration animation
        const effect = document.createElement('div');
        effect.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            font-size: 3em;
            pointer-events: none;
            animation: milestone-celebration 2s ease-out forwards;
        `;
        effect.textContent = '🎉';
        document.body.appendChild(effect);
        
        setTimeout(() => effect.remove(), 2000);
    }
    
    startProgressionCheck() {
        // Check every 10 seconds
        this.checkInterval = setInterval(() => {
            this.checkAllStats();
        }, 10000);
    }
    
    stopProgressionCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }
    
    parseNumber(text) {
        if (!text) return null;
        const cleaned = text.replace(/[^\d.-]/g, '');
        const num = parseFloat(cleaned);
        return isNaN(num) ? null : num;
    }
}

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.progressionTriggers = new ProgressionTriggers();
    });
} else {
    window.progressionTriggers = new ProgressionTriggers();
}

