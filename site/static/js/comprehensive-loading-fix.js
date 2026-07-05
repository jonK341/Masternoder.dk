/**
 * Comprehensive Loading and Progress Fix
 * Ensures all loading states show progress and update properly
 */
class ComprehensiveLoadingFix {
    constructor() {
        this.loadingElements = new Map();
        this.progressIntervals = new Map();
        this.init();
    }
    
    init() {
        console.log('[LoadingFix] Initializing comprehensive loading fixes...');
        
        // Fix all skeleton loaders
        this.fixSkeletonLoaders();
        
        // Fix progress bars
        this.fixProgressBars();
        
        // Fix status displays
        this.fixStatusDisplays();
        
        // Monitor for new loading elements
        this.observeNewElements();
    }
    
    fixSkeletonLoaders() {
        const skeletonLoaders = document.querySelectorAll('.skeleton-loader');
        console.log(`[LoadingFix] Found ${skeletonLoaders.length} skeleton loaders`);
        
        skeletonLoaders.forEach((loader, index) => {
            // Add a timeout to show content after a delay
            setTimeout(() => {
                const parent = loader.parentElement;
                if (parent && parent.id) {
                    // Try to load content for this element
                    this.loadContentForElement(parent.id);
                }
            }, 1000 + (index * 100)); // Stagger loading
        });
    }
    
    fixProgressBars() {
        // Find all progress bars
        const progressBars = document.querySelectorAll('[id*="progress"], [class*="progress"]');
        
        progressBars.forEach(bar => {
            // Ensure progress bars are visible when they have progress
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        const width = bar.style.width || '0%';
                        const widthValue = parseInt(width);
                        if (widthValue > 0 && bar.style.display === 'none') {
                            bar.style.display = 'block';
                        }
                    }
                });
            });
            
            observer.observe(bar, { attributes: true, attributeFilter: ['style'] });
        });
    }
    
    fixStatusDisplays() {
        // Find all status elements
        const statusElements = document.querySelectorAll('[id*="status"], [class*="status"]');
        
        statusElements.forEach(status => {
            // Ensure status updates are visible
            if (status.textContent.includes('Loading') || status.textContent.includes('Processing')) {
                // Add pulse animation
                status.style.animation = 'pulse 2s infinite';
            }
        });
    }
    
    loadContentForElement(elementId) {
        // Map element IDs to load functions
        const loadFunctions = {
            'battle-stats': () => this.loadBattleStats(),
            'battle-inventory': () => this.loadBattleInventory(),
            'battle-artifacts': () => this.loadBattleArtifacts(),
            'battle-power-stats': () => this.loadBattlePowerStats(),
            'fantasy-resources': () => this.loadFantasyResources(),
            'rule-books-list': () => this.loadRuleBooks(),
            'battle-series-list': () => this.loadBattleSeries(),
            'battle-history': () => this.loadBattleHistory(),
            'battle-leaderboard': () => this.loadBattleLeaderboard(),
        };
        
        if (loadFunctions[elementId]) {
            loadFunctions[elementId]();
        }
    }
    
    async loadBattleStats() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/battle/stats/overview?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-stats')) {
                // Update stats display
                this.updateElement('battle-stats', data.stats);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle stats:', error);
        }
    }
    
    async loadBattleInventory() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/battle/resources/inventory?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-inventory')) {
                this.updateElement('battle-inventory', data.inventory);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle inventory:', error);
        }
    }
    
    async loadBattleArtifacts() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/battle/resources/artifacts?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-artifacts')) {
                this.updateElement('battle-artifacts', data.artifacts);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle artifacts:', error);
        }
    }
    
    async loadBattlePowerStats() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/unified/stats?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-power-stats')) {
                this.updateElement('battle-power-stats', data.stats);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle power stats:', error);
        }
    }
    
    async loadFantasyResources() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/battle/resources/fantasy?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('fantasy-resources')) {
                this.updateElement('fantasy-resources', data.resources);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load fantasy resources:', error);
        }
    }
    
    async loadRuleBooks() {
        try {
            const response = await fetch('/api/battle/rule-books');
            const data = await response.json();
            
            if (data.success && document.getElementById('rule-books-list')) {
                this.updateElement('rule-books-list', data.rule_books);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load rule books:', error);
        }
    }
    
    async loadBattleSeries() {
        try {
            const response = await fetch('/api/battle/series');
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-series-list')) {
                this.updateElement('battle-series-list', data.series);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle series:', error);
        }
    }
    
    async loadBattleHistory() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`/api/battle/history?user_id=${userId}`);
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-history')) {
                this.updateElement('battle-history', data.history);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle history:', error);
        }
    }
    
    async loadBattleLeaderboard() {
        try {
            const response = await fetch('/api/battle/leaderboard');
            const data = await response.json();
            
            if (data.success && document.getElementById('battle-leaderboard')) {
                this.updateElement('battle-leaderboard', data.leaderboard);
            }
        } catch (error) {
            console.warn('[LoadingFix] Could not load battle leaderboard:', error);
        }
    }
    
    updateElement(elementId, data) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Remove skeleton loader
        const skeleton = element.querySelector('.skeleton-loader');
        if (skeleton) {
            skeleton.remove();
        }
        
        // Update with actual content
        if (data && typeof data === 'object') {
            element.innerHTML = this.formatDataAsHTML(data);
        } else {
            element.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No data available</p>';
        }
    }
    
    formatDataAsHTML(data) {
        // Simple HTML formatter
        if (Array.isArray(data)) {
            return data.map(item => `
                <div class="battle-card" style="margin-bottom: var(--spacing-md);">
                    ${JSON.stringify(item, null, 2)}
                </div>
            `).join('');
        } else {
            return `
                <div class="battle-card">
                    <pre style="color: var(--text-primary);">${JSON.stringify(data, null, 2)}</pre>
                </div>
            `;
        }
    }
    
    observeNewElements() {
        // Watch for new skeleton loaders being added
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        if (node.classList && node.classList.contains('skeleton-loader')) {
                            // New skeleton loader added, fix it
                            setTimeout(() => {
                                this.fixSkeletonLoaders();
                            }, 100);
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.comprehensiveLoadingFix = new ComprehensiveLoadingFix();
    });
} else {
    window.comprehensiveLoadingFix = new ComprehensiveLoadingFix();
}
