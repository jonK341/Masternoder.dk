/**
 * Theme Timeline - Beautiful timeline-based theme selector
 */
class ThemeTimeline {
    constructor(containerId, onThemeSelect) {
        this.container = document.getElementById(containerId);
        this.onThemeSelect = onThemeSelect || (() => {});
        this.themes = [];
        this.userThemes = [];
        this.selectedTheme = null;
        this.currentCategory = 'all';
        this.apiBase = window.location.origin;
    }
    
    async init() {
        await this.loadThemes();
        await this.loadUserThemes();
        this.render();
    }
    
    async loadThemes() {
        try {
            const response = await fetch(`${this.apiBase}/api/themes/list`);
            const data = await response.json();
            if (data.success && data.themes) {
                this.themes = data.themes;
            }
        } catch (error) {
            console.error('Error loading themes:', error);
        }
    }
    
    async loadUserThemes() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            const response = await fetch(`${this.apiBase}/api/themes/user?user_id=${userId}`);
            const data = await response.json();
            if (data.success && data.themes) {
                this.userThemes = data.themes.map(t => t.theme_id);
            }
        } catch (error) {
            console.error('Error loading user themes:', error);
        }
    }
    
    render() {
        if (!this.container) return;
        
        const filteredThemes = this.getFilteredThemes();
        
        this.container.innerHTML = `
            <div class="theme-category-tabs">
                ${this.renderCategoryTabs()}
            </div>
            <div class="theme-timeline">
                ${filteredThemes.length > 0 
                    ? filteredThemes.map(theme => this.renderThemeCard(theme)).join('')
                    : this.renderEmptyState()
                }
            </div>
            ${this.selectedTheme ? this.renderThemeDetails() : ''}
        `;
        
        // Add event listeners
        this.attachEventListeners();
    }
    
    renderCategoryTabs() {
        const categories = [
            { id: 'all', name: 'All', icon: '🎨' },
            { id: 'historical', name: 'Historical', icon: '⚔️' },
            { id: 'fantasy', name: 'Fantasy', icon: '🃏' },
            { id: 'tech', name: 'Tech', icon: '⌨️' },
            { id: 'apocalyptic', name: 'Apocalyptic', icon: '💀' },
            { id: 'action', name: 'Action', icon: '⚡' },
            { id: 'battle', name: 'Battle', icon: '⚔️' }
        ];
        
        return categories.map(cat => `
            <button class="theme-category-tab ${this.currentCategory === cat.id ? 'active' : ''}" 
                    data-category="${cat.id}">
                ${cat.icon} ${cat.name}
            </button>
        `).join('');
    }
    
    renderThemeCard(theme) {
        const isUnlocked = this.userThemes.includes(theme.theme_id);
        const isSelected = this.selectedTheme && this.selectedTheme.theme_id === theme.theme_id;
        const isPremium = theme.metadata?.premium || false;
        
        const icon = this.getThemeIcon(theme.theme_id);
        const era = this.getThemeEra(theme);
        const badge = this.getThemeBadge(theme, isUnlocked, isPremium);
        
        return `
            <div class="theme-card ${isSelected ? 'selected' : ''} ${!isUnlocked ? 'locked' : ''}" 
                 data-theme-id="${theme.theme_id}"
                 data-unlocked="${isUnlocked}">
                <div class="theme-icon">${icon}</div>
                <div class="theme-name">${theme.name}</div>
                <div class="theme-era">${era}</div>
                ${badge}
            </div>
        `;
    }
    
    renderThemeDetails() {
        if (!this.selectedTheme) return '';
        
        const style = this.selectedTheme.style || {};
        const metadata = this.selectedTheme.metadata || {};
        const isUnlocked = this.userThemes.includes(this.selectedTheme.theme_id);
        
        return `
            <div class="theme-details">
                <h3>${this.selectedTheme.name}</h3>
                <p>${this.selectedTheme.description || 'No description available'}</p>
                
                <div class="theme-style-info">
                    ${style.mood ? `
                        <div class="theme-style-item">
                            <div class="theme-style-label">Mood</div>
                            <div class="theme-style-value">${style.mood}</div>
                        </div>
                    ` : ''}
                    ${style.visual_style ? `
                        <div class="theme-style-item">
                            <div class="theme-style-label">Style</div>
                            <div class="theme-style-value">${style.visual_style}</div>
                        </div>
                    ` : ''}
                    ${this.selectedTheme.category ? `
                        <div class="theme-style-item">
                            <div class="theme-style-label">Category</div>
                            <div class="theme-style-value">${this.selectedTheme.category}</div>
                        </div>
                    ` : ''}
                    ${metadata.difficulty ? `
                        <div class="theme-style-item">
                            <div class="theme-style-label">Difficulty</div>
                            <div class="theme-style-value">${metadata.difficulty}</div>
                        </div>
                    ` : ''}
                </div>
                
                <button class="theme-use-button" 
                        onclick="themeTimeline.useSelectedTheme()"
                        ${!isUnlocked ? 'disabled' : ''}>
                    ${isUnlocked ? '✓ Use This Theme' : '🔒 Theme Locked - Unlock in Shop'}
                </button>
            </div>
        `;
    }
    
    renderEmptyState() {
        return `
            <div class="theme-empty-state">
                <div class="theme-empty-state-icon">🎨</div>
                <p>Brug standard tema – skriv titel og beskrivelse ovenfor</p>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Category tab clicks
        this.container.querySelectorAll('.theme-category-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const category = e.target.dataset.category;
                this.filterByCategory(category);
            });
        });
        
        // Theme card clicks
        this.container.querySelectorAll('.theme-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const themeId = e.currentTarget.dataset.themeId;
                this.selectTheme(themeId);
            });
        });
    }
    
    filterByCategory(category) {
        this.currentCategory = category;
        this.render();
    }
    
    selectTheme(themeId) {
        this.selectedTheme = this.themes.find(t => t.theme_id === themeId);
        this.render();
    }
    
    useSelectedTheme() {
        if (this.selectedTheme) {
            this.onThemeSelect(this.selectedTheme.theme_id);
        }
    }
    
    getFilteredThemes() {
        if (this.currentCategory === 'all') {
            return this.themes;
        }
        return this.themes.filter(t => t.category === this.currentCategory);
    }
    
    getThemeIcon(themeId) {
        const icons = {
            'wwii': '⚔️',
            'mtg': '🃏',
            'ctrl_a_delete': '⌨️',
            'the_end': '💀',
            'slaprygler': '⚡',
            'voldsrov': '⚔️',
            'carchase': '🚗',
            'fire': '🔥',
            'blood': '🩸',
            'action': '⚡'
        };
        return icons[themeId] || '🎨';
    }
    
    getThemeEra(theme) {
        const style = theme.style || {};
        if (style.era) return style.era;
        if (theme.category === 'historical') return 'Historical';
        if (theme.category === 'fantasy') return 'Fantasy';
        if (theme.category === 'tech') return 'Tech';
        if (theme.category === 'apocalyptic') return 'Apocalyptic';
        if (theme.category === 'action') return 'Action';
        if (theme.category === 'battle') return 'Battle';
        return theme.category || 'Theme';
    }
    
    getThemeBadge(theme, isUnlocked, isPremium) {
        if (!isUnlocked) {
            return '<div class="theme-badge locked">🔒 Locked</div>';
        }
        if (isPremium) {
            return '<div class="theme-badge premium">⭐ Premium</div>';
        }
        return '<div class="theme-badge unlocked">✓ Unlocked</div>';
    }
}

// Global instance (use window to avoid duplicate declaration when inline scripts also reference themeTimeline)
window.themeTimeline = window.themeTimeline || null;

