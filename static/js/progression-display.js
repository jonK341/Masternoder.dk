/**
 * Progression Display System
 * Displays points and level progression across all sites
 */
class ProgressionDisplay {
    constructor() {
        this.baseUrl = window.location.origin;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.updateInterval = 30000; // 30 seconds
        this.progressionData = null;
    }
    
    /**
     * Initialize progression display
     */
    init() {
        this.loadProgression();
        this.createProgressionWidgets();
        setInterval(() => this.loadProgression(), this.updateInterval);
    }
    
    /**
     * Load progression data from API
     */
    async loadProgression() {
        try {
            const response = await fetch(`${this.baseUrl}/api/progression/all/${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.progressionData = data;
                this.updateAllDisplays();
            }
        } catch (error) {
            console.error('Error loading progression:', error);
        }
    }
    
    /**
     * Create progression widgets on page
     */
    createProgressionWidgets() {
        // Create main progression widget
        this.createMainProgressionWidget();
        
        // Create category progression widgets
        this.createCategoryWidgets();
    }
    
    /**
     * Create main progression widget
     */
    createMainProgressionWidget() {
        const widget = document.createElement('div');
        widget.id = 'progression-main-widget';
        widget.className = 'progression-widget';
        widget.innerHTML = `
            <div class="progression-header">
                <h3>📊 Overall Progression</h3>
            </div>
            <div class="progression-content">
                <div class="progression-level">
                    <span class="level-label">Level</span>
                    <span class="level-value" id="main-level">1</span>
                </div>
                <div class="progression-bar-container">
                    <div class="progression-bar" id="main-progress-bar">
                        <div class="progression-fill" id="main-progress-fill"></div>
                    </div>
                    <div class="progression-text" id="main-progress-text">0 / 0 XP</div>
                </div>
            </div>
        `;
        
        // Insert at top of page or in specific container
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(widget, container.firstChild);
        
        this.addProgressionStyles();
    }
    
    /**
     * Create category progression widgets
     */
    createCategoryWidgets() {
        const categories = ['battle', 'social', 'generation', 'quest', 'achievement', 'rights', 'shop'];
        const container = document.getElementById('progression-categories') || this.createCategoriesContainer();
        
        categories.forEach(category => {
            const widget = document.createElement('div');
            widget.className = 'progression-category-widget';
            widget.id = `progression-${category}`;
            widget.innerHTML = `
                <div class="category-header">
                    <span class="category-icon">${this.getCategoryIcon(category)}</span>
                    <span class="category-name">${this.getCategoryName(category)}</span>
                </div>
                <div class="category-level">
                    <span class="level-value" id="${category}-level">1</span>
                    <span class="level-name" id="${category}-level-name">Novice</span>
                </div>
                <div class="category-progress-bar">
                    <div class="progress-fill" id="${category}-progress-fill"></div>
                </div>
                <div class="category-progress-text" id="${category}-progress-text">0 / 0</div>
            `;
            container.appendChild(widget);
        });
    }
    
    /**
     * Create categories container
     */
    createCategoriesContainer() {
        const container = document.createElement('div');
        container.id = 'progression-categories';
        container.className = 'progression-categories-container';
        
        const mainWidget = document.getElementById('progression-main-widget');
        if (mainWidget && mainWidget.parentNode) {
            mainWidget.parentNode.insertBefore(container, mainWidget.nextSibling);
        } else {
            document.body.appendChild(container);
        }
        
        return container;
    }
    
    /**
     * Update all progression displays
     */
    updateAllDisplays() {
        if (!this.progressionData) return;
        
        const progressions = this.progressionData.progressions || {};
        
        // Update main progression
        if (progressions.main) {
            this.updateProgressionDisplay('main', progressions.main);
        }
        
        // Update category progressions
        Object.keys(progressions).forEach(category => {
            if (category !== 'main') {
                this.updateProgressionDisplay(category, progressions[category]);
            }
        });
    }
    
    /**
     * Update progression display for category
     */
    updateProgressionDisplay(category, progression) {
        // Update level
        const levelEl = document.getElementById(`${category}-level`);
        if (levelEl) {
            levelEl.textContent = progression.level || 1;
        }
        
        // Update level name
        const levelNameEl = document.getElementById(`${category}-level-name`);
        if (levelNameEl) {
            levelNameEl.textContent = progression.level_name || 'Novice';
        }
        
        // Update progress bar
        const progressFill = document.getElementById(`${category}-progress-fill`);
        if (progressFill) {
            progressFill.style.width = `${progression.progress_percent || 0}%`;
        }
        
        // Update progress text
        const progressText = document.getElementById(`${category}-progress-text`);
        if (progressText) {
            const current = progression.points_progress || progression.xp_progress || 0;
            const needed = progression.points_needed || progression.xp_needed || 0;
            progressText.textContent = `${current} / ${needed}`;
        }
        
        // Update main widget if main category
        if (category === 'main') {
            const mainLevel = document.getElementById('main-level');
            if (mainLevel) {
                mainLevel.textContent = progression.level || 1;
            }
            
            const mainFill = document.getElementById('main-progress-fill');
            if (mainFill) {
                mainFill.style.width = `${progression.progress_percent || 0}%`;
            }
            
            const mainText = document.getElementById('main-progress-text');
            if (mainText) {
                const current = progression.xp_progress || 0;
                const needed = progression.xp_needed || 0;
                mainText.textContent = `${current} / ${needed} XP`;
            }
        }
    }
    
    /**
     * Get category icon
     */
    getCategoryIcon(category) {
        const icons = {
            'battle': '⚔️',
            'social': '👥',
            'generation': '🎬',
            'quest': '📋',
            'achievement': '🏆',
            'rights': '⚖️',
            'shop': '🛒'
        };
        return icons[category] || '⭐';
    }
    
    /**
     * Get category name
     */
    getCategoryName(category) {
        const names = {
            'battle': 'Battle',
            'social': 'Social',
            'generation': 'Generation',
            'quest': 'Quest',
            'achievement': 'Achievement',
            'rights': 'Rights',
            'shop': 'Shop'
        };
        return names[category] || category;
    }
    
    /**
     * Add progression styles
     */
    addProgressionStyles() {
        if (document.getElementById('progression-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'progression-styles';
        style.textContent = `
            .progression-widget {
                background: linear-gradient(135deg, rgba(40, 40, 55, 0.95), rgba(30, 30, 45, 0.95));
                border: 2px solid rgba(0, 255, 136, 0.3);
                border-radius: 15px;
                padding: 20px;
                margin: 20px 0;
                backdrop-filter: blur(20px);
            }
            
            .progression-header h3 {
                color: var(--primary, #00ff88);
                margin: 0 0 15px 0;
                font-size: 1.2em;
            }
            
            .progression-level {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            
            .level-value {
                font-size: 2em;
                font-weight: 700;
                color: var(--primary, #00ff88);
            }
            
            .progression-bar-container {
                margin-top: 10px;
            }
            
            .progression-bar {
                width: 100%;
                height: 25px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 12px;
                overflow: hidden;
                position: relative;
            }
            
            .progression-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary, #00ff88), var(--secondary, #00d4ff));
                transition: width 0.5s ease;
                border-radius: 12px;
            }
            
            .progression-text {
                text-align: center;
                margin-top: 5px;
                color: var(--text-secondary, #888);
                font-size: 0.9em;
            }
            
            .progression-categories-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            
            .progression-category-widget {
                background: rgba(40, 40, 55, 0.8);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
            }
            
            .category-header {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                margin-bottom: 10px;
            }
            
            .category-icon {
                font-size: 1.5em;
            }
            
            .category-name {
                font-weight: 600;
                color: var(--text-primary, #fff);
            }
            
            .category-level {
                margin: 10px 0;
            }
            
            .category-level .level-value {
                font-size: 1.8em;
                font-weight: 700;
                color: var(--primary, #00ff88);
            }
            
            .category-level .level-name {
                display: block;
                font-size: 0.9em;
                color: var(--text-secondary, #888);
                margin-top: 5px;
            }
            
            .category-progress-bar {
                width: 100%;
                height: 15px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                overflow: hidden;
                margin: 10px 0;
            }
            
            .category-progress-bar .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary, #00ff88), var(--secondary, #00d4ff));
                transition: width 0.5s ease;
                border-radius: 8px;
            }
            
            .category-progress-text {
                font-size: 0.85em;
                color: var(--text-secondary, #888);
            }
        `;
        document.head.appendChild(style);
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const progressionDisplay = new ProgressionDisplay();
        progressionDisplay.init();
        window.progressionDisplay = progressionDisplay; // Make globally available
    });
} else {
    const progressionDisplay = new ProgressionDisplay();
    progressionDisplay.init();
    window.progressionDisplay = progressionDisplay;
}

