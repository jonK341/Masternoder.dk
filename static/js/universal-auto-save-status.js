/**
 * Universal Auto-Save Status
 * Adds auto-save status indicator to all pages
 */
class UniversalAutoSaveStatus {
    constructor() {
        this.statusElement = null;
        this.statusText = null;
        this.lastSaveTime = null;
        this.init();
    }

    init() {
        // Create status element if it doesn't exist
        if (!document.getElementById('universal-auto-save-status')) {
            this.createStatusElement();
        } else {
            this.statusElement = document.getElementById('universal-auto-save-status');
            this.statusText = document.getElementById('save-status-text');
        }

        // Listen for auto-save events
        document.addEventListener('autoSaveStatus', (e) => {
            this.updateStatus(e.detail.status, e.detail.message);
        });

        // Check auto-save status periodically
        this.checkStatus();
        setInterval(() => this.checkStatus(), 5000); // Every 5 seconds
    }

    createStatusElement() {
        const statusDiv = document.createElement('div');
        statusDiv.id = 'universal-auto-save-status';
        statusDiv.className = 'universal-auto-save-status';
        statusDiv.innerHTML = `
            <div class="auto-save-icon">
                <i class="fas fa-save" id="save-icon"></i>
            </div>
            <div class="auto-save-text">
                <span id="save-status-text">Ready</span>
                <span class="save-time" id="save-time-text"></span>
            </div>
        `;
        document.body.appendChild(statusDiv);
        
        this.statusElement = statusDiv;
        this.statusText = document.getElementById('save-status-text');
        
        // Add styles if not already added
        this.addStyles();
    }

    addStyles() {
        if (document.getElementById('universal-auto-save-styles')) return;

        const style = document.createElement('style');
        style.id = 'universal-auto-save-styles';
        style.textContent = `
            .universal-auto-save-status {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: var(--bg-card, rgba(20, 20, 30, 0.95));
                border: 2px solid var(--border-primary, rgba(0, 255, 136, 0.3));
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 0.85em;
                z-index: 10000;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }

            .universal-auto-save-status.saving {
                border-color: var(--primary, #00ff88);
                animation: pulse 1s infinite;
            }

            .universal-auto-save-status.error {
                border-color: #ff4444;
                background: rgba(255, 68, 68, 0.1);
            }

            .universal-auto-save-status.success {
                border-color: #00ff88;
                background: rgba(0, 255, 136, 0.1);
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            .auto-save-icon {
                font-size: 1.2em;
                color: var(--primary, #00ff88);
            }

            .auto-save-text {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }

            .auto-save-text span {
                color: var(--text-primary, #ffffff);
            }

            .save-time {
                font-size: 0.75em;
                color: var(--text-secondary, #888);
            }

            @media (max-width: 768px) {
                .universal-auto-save-status {
                    bottom: 10px;
                    right: 10px;
                    padding: 10px 12px;
                    font-size: 0.75em;
                }
            }
        `;
        document.head.appendChild(style);
    }

    async checkStatus() {
        try {
            const _uid = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
            const response = await fetch(`/api/auto-save/status?user_id=${_uid}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateStatus(data.status || 'ready', null, data.last_save_time);
                }
            }
        } catch (error) {
            // Silently fail - status check is optional
        }
    }

    updateStatus(status, message, lastSaveTime = null) {
        if (!this.statusElement || !this.statusText) return;

        // Remove all status classes
        this.statusElement.classList.remove('saving', 'error', 'success', 'ready');

        // Add appropriate class
        if (status === 'saving') {
            this.statusElement.classList.add('saving');
            this.statusText.textContent = message || 'Saving...';
            const icon = document.getElementById('save-icon');
            if (icon) icon.className = 'fas fa-spinner fa-spin';
        } else if (status === 'error') {
            this.statusElement.classList.add('error');
            this.statusText.textContent = message || 'Save Error';
            const icon = document.getElementById('save-icon');
            if (icon) icon.className = 'fas fa-exclamation-triangle';
        } else if (status === 'success' || status === 'saved') {
            this.statusElement.classList.add('success');
            this.statusText.textContent = message || 'Saved';
            const icon = document.getElementById('save-icon');
            if (icon) icon.className = 'fas fa-check';
            this.lastSaveTime = lastSaveTime || new Date();
        } else {
            this.statusElement.classList.add('ready');
            this.statusText.textContent = message || 'Ready';
            const icon = document.getElementById('save-icon');
            if (icon) icon.className = 'fas fa-save';
        }

        // Update last save time
        if (lastSaveTime || this.lastSaveTime) {
            const timeText = document.getElementById('save-time-text');
            if (timeText) {
                const time = lastSaveTime || this.lastSaveTime;
                const date = new Date(time);
                const now = new Date();
                const diff = Math.floor((now - date) / 1000);
                
                if (diff < 60) {
                    timeText.textContent = `${diff}s ago`;
                } else if (diff < 3600) {
                    timeText.textContent = `${Math.floor(diff / 60)}m ago`;
                } else {
                    timeText.textContent = date.toLocaleTimeString();
                }
            }
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new UniversalAutoSaveStatus();
    });
} else {
    new UniversalAutoSaveStatus();
}

