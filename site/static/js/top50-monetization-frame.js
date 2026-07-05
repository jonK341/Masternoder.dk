/**
 * Top 50 Monetization Frame
 * Displays top 50 with top 6 highlighted, trophies, and resources
 * With toggle switch for on/off
 */

class Top50MonetizationFrame {
    constructor() {
        this.baseURL = '/api/monetization';
        this.userId = this.getUserId();
        this.isEnabled = true;
        this.frame = null;
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        return 'default_user';
    }

    /**
     * Create the frame with toggle switch
     */
    createFrame() {
        // Remove existing frame if any
        const existing = document.getElementById('top50-monetization-frame');
        if (existing) existing.remove();

        // Create frame container
        this.frame = document.createElement('div');
        this.frame.id = 'top50-monetization-frame';
        this.frame.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 400px;
            max-height: 80vh;
            background: rgba(20, 20, 30, 0.98);
            border: 2px solid rgba(0, 255, 136, 0.5);
            border-radius: 16px;
            padding: 20px;
            z-index: 10000;
            backdrop-filter: blur(20px);
            box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3);
            overflow-y: auto;
            display: ${this.isEnabled ? 'block' : 'none'};
        `;

        // Header with toggle
        const header = document.createElement('div');
        header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;';
        
        const title = document.createElement('h3');
        title.textContent = '💰 Top 50 Monetization';
        title.style.cssText = 'color: #00ff88; margin: 0; font-size: 1.3rem;';
        
        // Toggle switch
        const toggleContainer = document.createElement('div');
        toggleContainer.style.cssText = 'display: flex; align-items: center; gap: 10px;';
        
        const toggleLabel = document.createElement('span');
        toggleLabel.textContent = this.isEnabled ? 'ON' : 'OFF';
        toggleLabel.style.cssText = 'color: #00ff88; font-size: 0.9rem;';
        
        const toggleSwitch = document.createElement('input');
        toggleSwitch.type = 'checkbox';
        toggleSwitch.checked = this.isEnabled;
        toggleSwitch.style.cssText = 'width: 50px; height: 25px; cursor: pointer;';
        toggleSwitch.onchange = (e) => {
            this.isEnabled = e.target.checked;
            toggleLabel.textContent = this.isEnabled ? 'ON' : 'OFF';
            this.frame.style.display = this.isEnabled ? 'block' : 'none';
            if (this.isEnabled) {
                this.loadTop50();
            }
        };
        
        toggleContainer.appendChild(toggleLabel);
        toggleContainer.appendChild(toggleSwitch);
        
        header.appendChild(title);
        header.appendChild(toggleContainer);
        
        // Content area
        const content = document.createElement('div');
        content.id = 'top50-content';
        content.style.cssText = 'min-height: 200px;';
        
        this.frame.appendChild(header);
        this.frame.appendChild(content);
        
        const container = document.getElementById('top50-monetization-frame-container');
        if (container) {
            container.innerHTML = '';
            container.appendChild(this.frame);
            this.frame.style.position = 'relative';
            this.frame.style.top = '0';
            this.frame.style.right = '0';
        } else {
            document.body.appendChild(this.frame);
        }
        
        // Load data if enabled
        if (this.isEnabled) {
            this.loadTop50();
        }
    }

    /**
     * Load top 50 data
     */
    async loadTop50() {
        const content = document.getElementById('top50-content');
        if (!content) return;

        content.innerHTML = '<div style="text-align: center; color: #888;">Loading...</div>';

        try {
            const top50Response = await fetch(`${this.baseURL}/top-50`);
            const top50Data = top50Response.ok ? await top50Response.json() : { success: false, top_50: [] };

            const top6Response = await fetch(`${this.baseURL}/top-6`);
            const top6Data = top6Response.ok ? await top6Response.json() : { success: false, top_6: [] };

            // Build HTML
            let html = '';

            // Top 6 section (highlighted)
            if (top6Data.success && top6Data.top_6.length > 0) {
                html += '<div style="margin-bottom: 30px;">';
                html += '<h4 style="color: #00ff88; margin-bottom: 15px; border-bottom: 2px solid rgba(0, 255, 136, 0.3); padding-bottom: 10px;">🏆 Top 6 Performers</h4>';
                
                top6Data.top_6.forEach((user, idx) => {
                    const trophy = top6Data.trophies?.top_6_trophies?.[user.user_id];
                    html += `
                        <div style="background: ${idx < 3 ? 'rgba(255, 215, 0, 0.1)' : 'rgba(0, 255, 136, 0.05)'}; 
                                    border: 2px solid ${idx < 3 ? 'rgba(255, 215, 0, 0.5)' : 'rgba(0, 255, 136, 0.3)'}; 
                                    border-radius: 12px; padding: 15px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-size: 1.2em; font-weight: bold; color: ${idx < 3 ? '#ffd700' : '#00ff88'};">
                                        #${user.rank} - ${user.user_id}
                                    </div>
                                    <div style="color: #00d4ff; margin-top: 5px;">
                                        💰 ${user.total_cash.toFixed(2)} cash
                                    </div>
                                    ${trophy ? `
                                        <div style="color: #ff6b9d; margin-top: 5px; font-size: 0.9em;">
                                            🏆 ${trophy.trophy.trophy_name}
                                        </div>
                                        <div style="color: #888; font-size: 0.85em; margin-top: 5px;">
                                            Resources: +${trophy.resources.resources.cash} cash, +${trophy.resources.resources.energy_mind} mind, +${trophy.resources.resources.energy_power} power
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
            }

            // Top 50 list
            if (top50Data.success && top50Data.top_50.length > 0) {
                html += '<div>';
                html += '<h4 style="color: #00d4ff; margin-bottom: 15px; border-bottom: 2px solid rgba(0, 212, 255, 0.3); padding-bottom: 10px;">📊 Top 50 Leaderboard</h4>';
                
                top50Data.top_50.forEach((user, idx) => {
                    if (idx >= 6) {  // Skip top 6 (already shown)
                        html += `
                            <div style="background: rgba(40, 40, 55, 0.5); border: 1px solid rgba(0, 255, 136, 0.2); 
                                        border-radius: 8px; padding: 10px; margin-bottom: 8px; display: flex; justify-content: space-between;">
                                <span style="color: #00ff88;">#${user.rank}</span>
                                <span style="color: #fff;">${user.user_id}</span>
                                <span style="color: #00d4ff;">💰 ${user.total_cash.toFixed(2)}</span>
                            </div>
                        `;
                    }
                });
                
                html += '</div>';
            }

            content.innerHTML = html || '<div style="text-align: center; color: #888;">No data available</div>';

        } catch (error) {
            console.warn('Top 50 API unavailable:', error.message);
            content.innerHTML = '<div style="text-align: center; color: #888;">No leaderboard data available</div>';
        }
    }

    /**
     * Initialize
     */
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createFrame());
        } else {
            this.createFrame();
        }
    }
}

// Global instance
window.top50MonetizationFrame = new Top50MonetizationFrame();
window.top50MonetizationFrame.init();

