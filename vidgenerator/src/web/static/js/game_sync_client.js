/**
 * Game Sync Client
 * Handles client-server synchronization for game mechanics
 */
class GameSyncClient {
    constructor() {
        this.userId = this.getOrCreateUserId();
        this.syncState = null;
        this.syncInterval = null;
        this.baseUrl = window.location.origin;
        this.lastSyncTime = null;
    }
    
    getOrCreateUserId() {
        let userId = localStorage.getItem('game_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('game_user_id', userId);
        }
        return userId;
    }
    
    async syncGameState(clientState) {
        """Sync game state with server"""
        try {
            const response = await fetch(`${this.baseUrl}/vidgenerator/api/game/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    client_state: clientState,
                    server_state: this.syncState?.game_state || {}
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.sync_result) {
                    this.syncState = data.sync_result;
                    this.lastSyncTime = new Date();
                    console.log('[GameSync] State synced:', data.sync_result);
                    return data.sync_result;
                }
            }
        } catch (error) {
            console.error('[GameSync] Sync failed:', error);
        }
        return null;
    }
    
    startAutoSync(intervalMs = 5000) {
        """Start automatic synchronization"""
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }
        
        this.syncInterval = setInterval(() => {
            const clientState = this.getCurrentClientState();
            this.syncGameState(clientState);
        }, intervalMs);
        
        console.log('[GameSync] Auto-sync started');
    }
    
    stopAutoSync() {
        """Stop automatic synchronization"""
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
            console.log('[GameSync] Auto-sync stopped');
        }
    }
    
    getCurrentClientState() {
        """Get current client game state"""
        // Get from localStorage or game state
        const state = {
            xp: parseInt(localStorage.getItem('game_xp') || '0'),
            level: parseInt(localStorage.getItem('game_level') || '1'),
            defense_actions: JSON.parse(localStorage.getItem('game_defense_actions') || '[]'),
            hack_actions: JSON.parse(localStorage.getItem('game_hack_actions') || '[]'),
            timestamp: new Date().toISOString()
        };
        
        return state;
    }
    
    updateClientState(updates) {
        """Update client state"""
        if (updates.xp !== undefined) {
            localStorage.setItem('game_xp', updates.xp.toString());
        }
        if (updates.level !== undefined) {
            localStorage.setItem('game_level', updates.level.toString());
        }
        if (updates.defense_actions) {
            localStorage.setItem('game_defense_actions', JSON.stringify(updates.defense_actions));
        }
        if (updates.hack_actions) {
            localStorage.setItem('game_hack_actions', JSON.stringify(updates.hack_actions));
        }
    }
}

// Global instance
window.gameSyncClient = new GameSyncClient();

// Auto-start sync when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.gameSyncClient) {
        window.gameSyncClient.startAutoSync(5000); // Sync every 5 seconds
    }
});

