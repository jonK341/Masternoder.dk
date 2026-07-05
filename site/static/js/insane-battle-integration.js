/**
 * Insane Battle Integration
 * Integration for insane battle system with extreme difficulty levels
 */

class InsaneBattleIntegration {
    constructor() {
        this.baseURL = '/api/insane-battle';
        this.userId = this.getUserId();
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        return 'default_user';
    }

    /**
     * Start an insane battle
     */
    async startInsaneBattle(battleType) {
        try {
            const response = await fetch(`${this.baseURL}/start`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    battle_type: battleType
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get insane battle status
     */
    async getBattleStatus(battleId) {
        try {
            const response = await fetch(`${this.baseURL}/status/${battleId}?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Complete an insane battle
     */
    async completeBattle(battleId) {
        try {
            const response = await fetch(`${this.baseURL}/complete`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    battle_id: battleId
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get available insane battle types
     */
    async getBattleTypes() {
        try {
            const response = await fetch(`${this.baseURL}/types`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get battle history
     */
    async getBattleHistory(limit = 10) {
        try {
            const response = await fetch(`${this.baseURL}/history?user_id=${this.userId}&limit=${limit}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }
}

// Global instance
const insaneBattleIntegration = new InsaneBattleIntegration();

// Helper functions for UI
async function startInsaneBattleUI(battleType) {
    const button = event.target;
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';

    try {
        const result = await insaneBattleIntegration.startInsaneBattle(battleType);
        
        if (result.success) {
            showNotification(`Insane Battle Started: ${battleType}`, 'success');
            // Update UI with battle info
            if (result.battle) {
                displayBattleInfo(result.battle);
            }
        } else {
            showNotification(`Error: ${result.error || 'Failed to start battle'}`, 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

function displayBattleInfo(battle) {
    // Create or update battle info display
    let battleInfo = document.getElementById('insane-battle-info');
    if (!battleInfo) {
        battleInfo = document.createElement('div');
        battleInfo.id = 'insane-battle-info';
        battleInfo.className = 'battle-info-card';
        document.querySelector('.battle-tab-content.active')?.appendChild(battleInfo);
    }

    battleInfo.innerHTML = `
        <div class="battle-info-header">
            <h3>${battle.battle_type} Battle</h3>
            <span class="battle-status ${battle.status}">${battle.status}</span>
        </div>
        <div class="battle-info-body">
            <p><strong>Cost:</strong> ${battle.cost || 0} points</p>
            <p><strong>Reward:</strong> ${battle.reward || 0} points</p>
            <p><strong>Difficulty:</strong> ${battle.difficulty || 'Extreme'}</p>
            <p><strong>Battle ID:</strong> ${battle.battle_id}</p>
        </div>
    `;
}

function showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#00ff88' : type === 'error' ? '#ff4444' : '#0088ff'};
        color: #000;
        border-radius: 10px;
        z-index: 10000;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

