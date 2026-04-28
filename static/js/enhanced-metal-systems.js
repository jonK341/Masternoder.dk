/**
 * Enhanced Metal Systems - Frontend Integration
 * Complete frontend for all metal systems
 */

class EnhancedMetalSystems {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.apiBase = '/api';
        this.stats = null;
        this.updateInterval = null;
        
        this.init();
    }

    async init() {
        // Create particles
        this.createParticles();
        
        // Initialize user if needed
        await this.initializeUser();
        
        // Load all data
        await this.loadAllData();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Request GPS permission
        this.requestGPSPermission();
    }

    createParticles() {
        const container = document.getElementById('particles');
        const count = 50;
        
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 20 + 's';
            particle.style.animationDuration = (Math.random() * 10 + 15) + 's';
            container.appendChild(particle);
        }
    }

    async initializeUser() {
        try {
            const response = await fetch(`${this.apiBase}/enhanced-metal/initialize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    console.log('User initialized with metal systems');
                }
            }
        } catch (error) {
            console.error('Error initializing user:', error);
        }
    }

    async loadAllData() {
        try {
            // Load all metal stats
            const response = await fetch(`${this.apiBase}/enhanced-metal/stats?user_id=${this.userId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.stats = data;
                    this.renderMetalSystems(data);
                    this.renderZeroStats(data.zero_points_stats || {});
                    this.renderGPS(data.gps_location || {});
                    this.renderStreetMinds(data.street_minds || {});
                    this.renderHashes(data.refresh_hashes || {});
                }
            }
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load metal systems data');
        }
    }

    renderMetalSystems(data) {
        const grid = document.getElementById('metalSystemsGrid');
        
        const metals = [
            {
                name: 'Territory Metal',
                icon: '🗺️',
                data: data.territory_metal,
                color: '#00ff88'
            },
            {
                name: 'Sex Metal',
                icon: '💋',
                data: data.sex_metal,
                color: '#ff0066'
            },
            {
                name: 'Porno Rights Metal',
                icon: '⚖️',
                data: data.porno_rights_metal,
                color: '#ff6600'
            },
            {
                name: 'MTG Metal',
                icon: '🃏',
                data: data.mtg_metal,
                color: '#6600ff'
            },
            {
                name: 'Trophy Hunt Metal',
                icon: '🏆',
                data: data.trophy_hunt_metal,
                color: '#ffaa00'
            }
        ];

        grid.innerHTML = metals.map(metal => {
            const metalData = metal.data || {};
            const level = metalData.territory_level || metalData.sex_metal_level || 
                        metalData.rights_level || metalData.mtg_level || metalData.hunt_level || 1;
            const points = metalData.territory_points || metalData.sex_metal_points || 
                          metalData.rights_points || metalData.mtg_points || metalData.hunt_points || 0;
            const nextLevelPoints = level * (metal.name === 'MTG Metal' ? 600 : 
                                           metal.name === 'Porno Rights Metal' ? 400 : 
                                           metal.name === 'Sex Metal' ? 300 : 500);
            const progress = Math.min((points / nextLevelPoints) * 100, 100);
            
            let extraStats = '';
            if (metal.name === 'MTG Metal') {
                extraStats = `
                    <div class="metal-stat">
                        <div class="metal-stat-label">Mana Power</div>
                        <div class="metal-stat-value">${metalData.mana_power || 100}</div>
                    </div>
                    <div class="metal-stat">
                        <div class="metal-stat-label">Spells</div>
                        <div class="metal-stat-value">${(metalData.spells_unlocked || []).length}</div>
                    </div>
                `;
            } else if (metal.name === 'Trophy Hunt Metal') {
                extraStats = `
                    <div class="metal-stat">
                        <div class="metal-stat-label">Trophies</div>
                        <div class="metal-stat-value">${metalData.trophies_collected || 0}</div>
                    </div>
                `;
            } else if (metal.name === 'Territory Metal') {
                extraStats = `
                    <div class="metal-stat">
                        <div class="metal-stat-label">Territories</div>
                        <div class="metal-stat-value">${(metalData.controlled_territories || []).length}</div>
                    </div>
                `;
            }

            return `
                <div class="metal-card">
                    <div class="metal-card-header">
                        <div>
                            <span class="metal-icon">${metal.icon}</span>
                            <h3 class="metal-name">${metal.name}</h3>
                        </div>
                        <span class="metal-level">Level ${level}</span>
                    </div>
                    <div class="metal-stats">
                        <div class="metal-stat">
                            <div class="metal-stat-label">Points</div>
                            <div class="metal-stat-value">${points.toLocaleString()}</div>
                        </div>
                        <div class="metal-stat">
                            <div class="metal-stat-label">Next Level</div>
                            <div class="metal-stat-value">${nextLevelPoints.toLocaleString()}</div>
                        </div>
                        ${extraStats}
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderZeroStats(zeroStats) {
        const grid = document.getElementById('zeroStatsGrid');
        
        // Select key stats to display
        const keyStats = [
            { key: 'battle_wins', label: 'Battle Wins', icon: '⚔️' },
            { key: 'videos_created', label: 'Videos Created', icon: '🎬' },
            { key: 'total_xp', label: 'Total XP', icon: '⭐' },
            { key: 'coins', label: 'Coins', icon: '🪙' },
            { key: 'achievements_earned', label: 'Achievements', icon: '🏅' },
            { key: 'friends_count', label: 'Friends', icon: '👥' },
            { key: 'login_streak', label: 'Login Streak', icon: '🔥' },
            { key: 'trophies_collected', label: 'Trophies', icon: '🏆' },
            { key: 'guild_memberships', label: 'Guilds', icon: '🛡️' },
            { key: 'clan_memberships', label: 'Clans', icon: '⚡' },
            { key: 'stats_points_total', label: 'Stats Points', icon: '📊' },
            { key: 'metal_points_total', label: 'Metal Points', icon: '⚡' }
        ];

        grid.innerHTML = keyStats.map(stat => {
            const value = zeroStats[stat.key] || 0;
            return `
                <div class="zero-stat-card">
                    <div class="zero-stat-value">${value.toLocaleString()}</div>
                    <div class="zero-stat-label">${stat.icon} ${stat.label}</div>
                </div>
            `;
        }).join('');

        // Add expand button
        const expandBtn = document.createElement('button');
        expandBtn.className = 'btn btn-primary';
        expandBtn.style.marginTop = '20px';
        expandBtn.style.width = '100%';
        expandBtn.textContent = 'View All 80+ Stats';
        expandBtn.onclick = () => this.showAllStats(zeroStats);
        grid.parentElement.appendChild(expandBtn);
    }

    showAllStats(zeroStats) {
        // Create modal or expandable section
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 10000;
            overflow-y: auto;
            padding: 40px;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(20, 20, 30, 0.95);
            border: 2px solid var(--primary);
            border-radius: 20px;
            padding: 40px;
        `;

        const categories = {
            'Battle': ['battle_wins', 'battle_losses', 'battle_draws', 'battle_streak', 'total_battles', 'battle_points'],
            'Social': ['friends_count', 'followers_count', 'following_count', 'social_points', 'social_interactions', 'messages_sent', 'messages_received'],
            'Economic': ['coins', 'credits', 'tokens', 'total_earned', 'total_spent', 'economic_value'],
            'Activity': ['daily_logins', 'login_streak', 'longest_streak', 'total_sessions', 'session_time', 'actions_today', 'actions_total'],
            'Achievement': ['achievements_earned', 'achievement_points', 'trophies_collected', 'badges_earned', 'medals_earned'],
            'Video': ['videos_created', 'videos_watched', 'videos_shared', 'videos_liked', 'videos_commented', 'total_watch_time'],
            'XP': ['total_xp', 'xp_today', 'xp_this_week', 'xp_this_month', 'xp_from_videos', 'xp_from_battles', 'xp_from_achievements'],
            'Network': ['guild_memberships', 'clan_memberships', 'guild_contributions', 'clan_contributions', 'war_participations']
        };

        let html = '<h2 style="color: var(--primary); margin-bottom: 30px;">All Zero Points Stats</h2>';
        
        Object.entries(categories).forEach(([category, keys]) => {
            html += `<h3 style="color: var(--secondary); margin: 30px 0 15px;">${category}</h3>`;
            html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">';
            keys.forEach(key => {
                const value = zeroStats[key] || 0;
                html += `
                    <div style="background: rgba(0, 255, 136, 0.05); border: 1px solid rgba(0, 255, 136, 0.2); border-radius: 10px; padding: 15px; text-align: center;">
                        <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${value.toLocaleString()}</div>
                        <div style="font-size: 0.8em; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;">${key.replace(/_/g, ' ')}</div>
                    </div>
                `;
            });
            html += '</div>';
        });

        content.innerHTML = html;

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.className = 'btn btn-primary';
        closeBtn.style.marginTop = '20px';
        closeBtn.onclick = () => modal.remove();
        content.appendChild(closeBtn);

        modal.appendChild(content);
        document.body.appendChild(modal);
    }

    renderGPS(gpsData) {
        const display = document.getElementById('gpsDisplay');
        
        if (!gpsData || !gpsData.lat) {
            display.innerHTML = `
                <div class="gps-info" style="grid-column: 1 / -1;">
                    <div class="gps-label">Status</div>
                    <div class="gps-value">No GPS Data</div>
                    <button class="btn btn-primary" style="margin-top: 15px;" onclick="enhancedMetal.requestGPSPermission()">
                        Enable GPS Tracking
                    </button>
                </div>
            `;
            return;
        }

        display.innerHTML = `
            <div class="gps-info">
                <div class="gps-label">Latitude</div>
                <div class="gps-value">${gpsData.lat.toFixed(6)}</div>
            </div>
            <div class="gps-info">
                <div class="gps-label">Longitude</div>
                <div class="gps-value">${gpsData.lng.toFixed(6)}</div>
            </div>
            <div class="gps-info">
                <div class="gps-label">Country</div>
                <div class="gps-value">${gpsData.country || 'Unknown'}</div>
            </div>
            <div class="gps-info">
                <div class="gps-label">City</div>
                <div class="gps-value">${gpsData.city || 'Unknown'}</div>
            </div>
        `;
    }

    renderStreetMinds(streetMinds) {
        const grid = document.getElementById('connectionsGrid');
        
        const connections = [
            { name: 'Territory Metal', key: 'territory_connection', icon: '🗺️' },
            { name: 'Sex Metal', key: 'sex_connection', icon: '💋' },
            { name: 'Porno Rights Metal', key: 'porno_rights_connection', icon: '⚖️' },
            { name: 'MTG Metal', key: 'mtg_connection', icon: '🃏' },
            { name: 'Trophy Hunt Metal', key: 'trophy_hunt_connection', icon: '🏆' }
        ];

        grid.innerHTML = connections.map(conn => {
            const connected = streetMinds[conn.key] || false;
            return `
                <div class="connection-card ${connected ? 'connected' : ''}">
                    <div class="connection-icon">${conn.icon}</div>
                    <div class="connection-name">${conn.name}</div>
                    <div class="connection-status">${connected ? '✅ Connected' : '❌ Not Connected'}</div>
                    ${!connected ? `
                        <button class="btn btn-primary" style="margin-top: 10px; width: 100%;" 
                                onclick="enhancedMetal.connectMetal('${conn.key.replace('_connection', '')}')">
                            Connect
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');

        // Add mind level display
        const mindLevel = document.createElement('div');
        mindLevel.style.cssText = 'text-align: center; margin-top: 30px; padding: 20px; background: rgba(0, 255, 136, 0.1); border-radius: 15px;';
        mindLevel.innerHTML = `
            <div style="font-size: 1.2em; color: var(--text-secondary); margin-bottom: 10px;">Street Minds Level</div>
            <div style="font-size: 3em; font-weight: 700; color: var(--primary);">${streetMinds.mind_level || 1}</div>
        `;
        grid.parentElement.appendChild(mindLevel);
    }

    renderHashes(hashes) {
        const display = document.getElementById('hashDisplay');
        
        if (!hashes || Object.keys(hashes).length === 0) {
            display.textContent = 'No hashes available';
            return;
        }

        let html = '';
        Object.entries(hashes).forEach(([system, hashData]) => {
            html += `<div style="margin-bottom: 15px;">`;
            html += `<strong style="color: var(--primary);">${system.toUpperCase()}:</strong><br>`;
            html += `<span style="color: var(--text-secondary);">${hashData.hash || 'N/A'}</span><br>`;
            html += `<small style="color: var(--text-tertiary);">${hashData.timestamp || ''}</small>`;
            html += `</div>`;
        });

        display.innerHTML = html;
    }

    async requestGPSPermission() {
        if (!navigator.geolocation) {
            this.showError('Geolocation is not supported by your browser');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                try {
                    const response = await fetch(`${this.apiBase}/enhanced-metal/gps/update`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: this.userId,
                            lat: lat,
                            lng: lng
                        })
                    });

                    if (response.ok) {
                        await this.loadAllData();
                        if (window.toast) {
                            window.toast.success('GPS location updated!');
                        }
                    }
                } catch (error) {
                    console.error('Error updating GPS:', error);
                }
            },
            (error) => {
                this.showError('GPS permission denied or unavailable');
            }
        );
    }

    async connectMetal(metalType) {
        try {
            const response = await fetch(`${this.apiBase}/enhanced-metal/street-minds/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    metal_type: metalType
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    await this.loadAllData();
                    if (window.toast) {
                        window.toast.success(`${metalType} connected to Street Minds!`);
                    }
                }
            }
        } catch (error) {
            console.error('Error connecting metal:', error);
            this.showError('Failed to connect metal system');
        }
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.updateInterval = setInterval(() => {
            this.loadAllData();
        }, 30000);
    }

    showError(message) {
        if (window.toast) {
            window.toast.error(message);
        } else {
            console.error(message);
        }
    }
}

// Initialize when DOM is ready
let enhancedMetal;
document.addEventListener('DOMContentLoaded', () => {
    enhancedMetal = new EnhancedMetalSystems();
    window.enhancedMetal = enhancedMetal; // Make globally available
});

