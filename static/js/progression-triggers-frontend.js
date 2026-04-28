/**
 * Progression Triggers Frontend
 * Connects all DOM elements and triggers progression saves
 */
class ProgressionTriggersFrontend {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.observers = [];
        this.triggers = new Map();
        
        this.init();
    }
    
    init() {
        // Watch all point counter elements
        this.setupDOMObservers();
        
        // Listen for point updates
        this.setupEventListeners();
        
        // Initialize progression triggers for all stats
        this.initializeAllTriggers();
    }
    
    setupDOMObservers() {
        // Observe all elements with point-related attributes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    this.handleDOMChange(mutation.target);
                }
            });
        });
        
        // Observe document body
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });
        
        this.observers.push(observer);
    }
    
    setupEventListeners() {
        // Listen for custom point update events
        document.addEventListener('pointsUpdated', (event) => {
            this.triggerProgression(event.detail.statName, event.detail.value);
        });
        
        // Listen for stat changes
        document.addEventListener('statChanged', (event) => {
            this.triggerProgression(event.detail.statName, event.detail.value);
        });
        
        // Listen for any input/change events on point-related elements
        document.addEventListener('input', (event) => {
            if (event.target.hasAttribute('data-point-type')) {
                const statName = event.target.getAttribute('data-point-type');
                const value = this.extractNumericValue(event.target.value);
                if (value !== null) {
                    this.triggerProgression(statName, value);
                }
            }
        });
    }
    
    initializeAllTriggers() {
        // Initialize triggers for all known stats
        const stats = [
            'xp_total', 'level', 'stats_points_total', 'achievement_points',
            'battle_points', 'generation_points', 'quest_points', 'social_points',
            'rights_points', 'reward_points', 'activity_points', 'coins', 'credits'
        ];
        
        stats.forEach((stat) => {
            this.addProgressionTrigger(stat);
        });
    }
    
    addProgressionTrigger(statName) {
        // Find DOM elements for this stat
        const selectors = [
            `[data-point-type="${statName}"]`,
            `[id*="${statName}"]`,
            `[class*="${statName}"]`
        ];
        
        selectors.forEach((selector) => {
            document.querySelectorAll(selector).forEach((el) => {
                this.observeElement(el, statName);
            });
        });
        
        this.triggers.set(statName, {
            statName,
            selectors,
            lastValue: null
        });
    }
    
    observeElement(element, statName) {
        // Watch this specific element
        const observer = new MutationObserver(() => {
            const value = this.extractNumericValue(element.textContent);
            if (value !== null) {
                this.triggerProgression(statName, value);
            }
        });
        
        observer.observe(element, {
            childList: true,
            subtree: true,
            characterData: true
        });
        
        this.observers.push(observer);
    }
    
    handleDOMChange(element) {
        // Check if element is a point counter
        const statName = element.getAttribute('data-point-type') ||
                        element.id?.replace(/[^a-zA-Z]/g, '') ||
                        element.className?.split(' ').find(c => c.includes('point'));
        
        if (statName) {
            const value = this.extractNumericValue(element.textContent);
            if (value !== null) {
                this.triggerProgression(statName, value);
            }
        }
    }
    
    async triggerProgression(statName, statValue) {
        try {
            // Check if value actually changed
            const trigger = this.triggers.get(statName);
            if (trigger && trigger.lastValue === statValue) {
                return; // No change
            }
            
            if (trigger) {
                trigger.lastValue = statValue;
            }
            
            // Trigger progression save
            const response = await fetch('/api/progression-triggers/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    stat_name: statName,
                    stat_value: statValue
                })
            });
            
            const result = await response.json();
            
            // Check progression level
            const levelResponse = await fetch(`/api/progression-triggers/check-level?user_id=${this.userId}&stat_name=${statName}&stat_value=${statValue}`);
            const levelResult = await levelResponse.json();
            
            // Emit event for other systems
            document.dispatchEvent(new CustomEvent('progressionTriggered', {
                detail: {
                    statName,
                    statValue,
                    result,
                    levelResult
                }
            }));
            
            return result;
        } catch (error) {
            console.error('[ProgressionTriggers] Error:', error);
            return { success: false, error: error.message };
        }
    }
    
    extractNumericValue(text) {
        if (!text) return null;
        const match = text.match(/[\d,]+/);
        if (match) {
            return parseInt(match[0].replace(/,/g, ''), 10);
        }
        return null;
    }
}

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.progressionTriggers = new ProgressionTriggersFrontend();
    });
} else {
    window.progressionTriggers = new ProgressionTriggersFrontend();
}

