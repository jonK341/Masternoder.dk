/**
 * Comprehensive Page Integration
 * Adds missing links, routes, points, energy, and integrations to all pages
 */

class ComprehensivePageIntegration {
    constructor() {
        this.baseURL = '/api';
        this.userId = this.getUserId();
        this.pages = [
            {name: 'index', url: '/', title: 'Home'},
            {name: 'generator', url: '/generator/', title: 'Generator'},
            {name: 'gallery', url: '/gallery/', title: 'Gallery'},
            {name: 'game', url: '/game/', title: 'Game'},
            {name: 'battle', url: '/battle/', title: 'Battle'},
            {name: 'stats', url: '/stats/', title: 'Stats'},
            {name: 'profile', url: '/profile/', title: 'Profile'},
            {name: 'social', url: '/social/', title: 'Social'},
            {name: 'shop', url: '/shop/', title: 'Shop'},
            {name: 'chat', url: '/chat/', title: 'Chat'},
            {name: 'debugger', url: '/debugger/', title: 'Debugger'},
            {name: 'analytics', url: '/analytics/', title: 'Analytics'},
            {name: 'dashboard', url: '/dashboard/', title: 'Dashboard'},
            {name: 'aggregator', url: '/aggregator/', title: 'Aggregator'},
            {name: 'metal', url: '/metal/', title: 'Metal'},
            {name: 'theme-points', url: '/theme-points/', title: 'Theme Points'},
            {name: 'rights-law', url: '/rights-law/', title: 'Rights Law'},
            {name: 'quests', url: '/quests/', title: 'Quests'},
            {name: 'battlegrounds', url: '/battlegrounds/', title: 'Battlegrounds'},
            {name: 'champions-league', url: '/champions-league/', title: 'Champions League'},
            {name: 'victory-tech-tree', url: '/victory-tech-tree/', title: 'Victory Tech Tree'},
            {name: 'danish-divine-tech-tree', url: '/danish-divine-tech-tree/', title: 'Danish Divine Tech Tree'},
            {name: 'academic-perspective', url: '/academic-perspective/', title: 'Academic Perspective'},
            {name: 'milkyway', url: '/milkyway/', title: 'Milkyway'},
            {name: 'editor', url: '/editor/', title: 'Editor'},
            {name: 'monetization', url: '/monetization/', title: 'Monetization'},
            {name: 'beta_testing', url: '/beta_testing/', title: 'Beta Testing'},
            {name: 'advanced_calculator', url: '/advanced_calculator/', title: 'Advanced Calculator'},
            {name: 'theme_premium', url: '/theme_premium/', title: 'Theme Premium'},
            {name: 'leaderboards', url: '/leaderboards/', title: 'Leaderboards'},
            {name: 'time-achievement-guides', url: '/time-achievement-guides/', title: 'Time Achievement Guides'},
        ];
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        return 'default_user';
    }

    /**
     * Add navigation links to page if missing
     */
    addNavigationLinks() {
        // Check if navigation exists
        if (document.querySelector('.navigation-toolbar') || document.querySelector('.nav-link')) {
            return; // Navigation already exists
        }

        // Create navigation container
        const nav = document.createElement('div');
        nav.className = 'comprehensive-navigation';
        nav.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(10, 10, 15, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(0, 255, 136, 0.3);
            padding: 15px 20px;
            z-index: 10000;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
            overflow-x: auto;
        `;

        // Add links
        this.pages.slice(0, 15).forEach(page => {
            const link = document.createElement('a');
            link.href = page.url;
            link.className = 'nav-link';
            link.textContent = page.title;
            link.style.cssText = `
                color: #00ff88;
                text-decoration: none;
                padding: 8px 15px;
                border-radius: 8px;
                transition: all 0.3s;
                white-space: nowrap;
            `;
            link.onmouseover = () => {
                link.style.background = 'rgba(0, 255, 136, 0.2)';
            };
            link.onmouseout = () => {
                link.style.background = 'transparent';
            };
            nav.appendChild(link);
        });

        // Insert at top of body
        document.body.insertBefore(nav, document.body.firstChild);
        
        // Add padding to body to account for fixed nav
        document.body.style.paddingTop = '60px';
    }

    /**
     * Add points and energy display
     */
    async addPointsEnergyDisplay() {
        // Check if display exists
        if (document.getElementById('comprehensive-points-energy-display')) {
            return;
        }

        // Get unified points and energy
        let pointsData = {success: false};
        let energyData = {success: false};

        try {
            if (window.comprehensiveAPI) {
                pointsData = await window.comprehensiveAPI.getPointsJSON();
                energyData = await window.comprehensiveAPI.getEnergyStatus();
            }
        } catch (error) {
            console.error('Error loading points/energy:', error);
        }

        // Create display
        const display = document.createElement('div');
        display.id = 'comprehensive-points-energy-display';
        display.style.cssText = `
            position: fixed;
            top: 60px;
            right: 20px;
            background: rgba(40, 40, 55, 0.95);
            padding: 20px;
            border-radius: 16px;
            border: 2px solid rgba(0, 255, 136, 0.3);
            backdrop-filter: blur(20px);
            z-index: 9999;
            min-width: 250px;
            max-width: 300px;
        `;

        display.innerHTML = `
            <h3 style="color: #00ff88; margin: 0 0 15px 0; font-size: 1.2rem;">
                <i class="fas fa-chart-line"></i> Points & Energy
            </h3>
            <div id="points-display-content">
                ${pointsData.success ? `
                    <div style="margin-bottom: 10px;">
                        <div style="color: #00d4ff; font-size: 0.9em;">Total Points</div>
                        <div style="font-size: 1.5em; font-weight: bold;">${pointsData.points?.total || 0}</div>
                    </div>
                ` : '<div style="color: #888;">Loading points...</div>'}
            </div>
            <div id="energy-display-content" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(0, 255, 136, 0.2);">
                ${energyData.success ? `
                    <div style="margin-bottom: 5px;">
                        <span style="color: #00ff88; font-size: 0.85em;">Mind:</span>
                        <span style="float: right;">${energyData.energy?.mind || 0}/100</span>
                    </div>
                    <div style="margin-bottom: 5px;">
                        <span style="color: #00ff88; font-size: 0.85em;">Power:</span>
                        <span style="float: right;">${energyData.energy?.power || 0}/100</span>
                    </div>
                    <div style="margin-bottom: 5px;">
                        <span style="color: #00ff88; font-size: 0.85em;">Time:</span>
                        <span style="float: right;">${energyData.energy?.time || 0}/100</span>
                    </div>
                    <div>
                        <span style="color: #00ff88; font-size: 0.85em;">Place:</span>
                        <span style="float: right;">${energyData.energy?.place || 0}/100</span>
                    </div>
                ` : '<div style="color: #888;">Loading energy...</div>'}
            </div>
            <button onclick="window.comprehensivePageIntegration.refreshPointsEnergy()" 
                    style="margin-top: 15px; width: 100%; padding: 8px; background: rgba(0, 255, 136, 0.2); 
                           border: 1px solid #00ff88; border-radius: 8px; color: #00ff88; cursor: pointer;">
                <i class="fas fa-sync"></i> Refresh
            </button>
        `;

        document.body.appendChild(display);
    }

    /**
     * Refresh points and energy display
     */
    async refreshPointsEnergy() {
        try {
            if (window.comprehensiveAPI) {
                const pointsData = await window.comprehensiveAPI.getPointsJSON(true);
                const energyData = await window.comprehensiveAPI.getEnergyStatus();

                // Update points display
                const pointsContent = document.getElementById('points-display-content');
                if (pointsContent && pointsData.success) {
                    pointsContent.innerHTML = `
                        <div style="margin-bottom: 10px;">
                            <div style="color: #00d4ff; font-size: 0.9em;">Total Points</div>
                            <div style="font-size: 1.5em; font-weight: bold;">${pointsData.points?.total || 0}</div>
                        </div>
                    `;
                }

                // Update energy display
                const energyContent = document.getElementById('energy-display-content');
                if (energyContent && energyData.success) {
                    energyContent.innerHTML = `
                        <div style="margin-bottom: 5px;">
                            <span style="color: #00ff88; font-size: 0.85em;">Mind:</span>
                            <span style="float: right;">${energyData.energy?.mind || 0}/100</span>
                        </div>
                        <div style="margin-bottom: 5px;">
                            <span style="color: #00ff88; font-size: 0.85em;">Power:</span>
                            <span style="float: right;">${energyData.energy?.power || 0}/100</span>
                        </div>
                        <div style="margin-bottom: 5px;">
                            <span style="color: #00ff88; font-size: 0.85em;">Time:</span>
                            <span style="float: right;">${energyData.energy?.time || 0}/100</span>
                        </div>
                        <div>
                            <span style="color: #00ff88; font-size: 0.85em;">Place:</span>
                            <span style="float: right;">${energyData.energy?.place || 0}/100</span>
                        </div>
                    `;
                }

                if (window.showToast) {
                    window.showToast('Points & Energy refreshed', 'success');
                }
            }
        } catch (error) {
            console.error('Error refreshing points/energy:', error);
            if (window.showToast) {
                window.showToast('Error refreshing data', 'error');
            }
        }
    }

    /**
     * Initialize comprehensive integration
     */
    init() {
        // Wait for DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        // Add navigation
        this.addNavigationLinks();

        // Add points/energy display
        this.addPointsEnergyDisplay();

        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.refreshPointsEnergy();
        }, 30000);
    }
}

// Global instance
window.comprehensivePageIntegration = new ComprehensivePageIntegration();
window.comprehensivePageIntegration.init();

