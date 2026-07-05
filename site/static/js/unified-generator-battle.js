/**
 * Unified Generator and Quick Battle Integration
 * Makes both systems work together seamlessly
 */
class UnifiedGeneratorBattle {
    constructor(baseUrl = '', userId = 'default_user') {
        this.BASE_URL = baseUrl;
        this.userId = userId;
        this.init();
    }
    
    async init() {
        console.log('[UnifiedGeneratorBattle] Initializing...');
        
        // Check services status
        await this.checkServicesStatus();
        
        // Initialize Epic Gaming if available
        if (window.epicGaming) {
            console.log('[UnifiedGeneratorBattle] Epic Gaming Experience available');
        }
    }
    
    async checkServicesStatus() {
        try {
            const response = await fetch(`${this.BASE_URL}/api/unified/status`);
            const data = await response.json();
            
            if (data.success) {
                console.log('[UnifiedGeneratorBattle] Services status:', data.services);
                return data.services;
            }
        } catch (error) {
            console.error('[UnifiedGeneratorBattle] Error checking status:', error);
        }
        return null;
    }
    
    async generateVideo(prompt, duration = 5, resolution = '1280x768') {
        try {
            console.log('[UnifiedGeneratorBattle] Generating video...', prompt);
            
            const response = await fetch(`${this.BASE_URL}/api/unified/generate-video`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: prompt,
                    user_id: this.userId,
                    duration: duration,
                    resolution: resolution
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[UnifiedGeneratorBattle] Video generated:', data);
                
                // Show success notification
                if (window.showToast) {
                    window.showToast('Video generation started!', 'success');
                }
                
                return data;
            } else {
                console.error('[UnifiedGeneratorBattle] Generation failed:', data.error);
                if (window.showToast) {
                    window.showToast(`Generation failed: ${data.error}`, 'error');
                }
                return data;
            }
        } catch (error) {
            console.error('[UnifiedGeneratorBattle] Error generating video:', error);
            if (window.showToast) {
                window.showToast('Error generating video', 'error');
            }
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async createBattle(difficulty = 'balanced', opponentType = 'ai') {
        try {
            console.log('[UnifiedGeneratorBattle] Creating battle...', difficulty);
            
            const response = await fetch(`${this.BASE_URL}/api/unified/create-battle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    difficulty: difficulty,
                    opponent_type: opponentType
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[UnifiedGeneratorBattle] Battle created:', data);
                
                // Show success notification
                if (window.showToast) {
                    window.showToast('Battle created!', 'success');
                }
                
                return data;
            } else {
                console.error('[UnifiedGeneratorBattle] Battle creation failed:', data.error);
                if (window.showToast) {
                    window.showToast(`Battle creation failed: ${data.error}`, 'error');
                }
                return data;
            }
        } catch (error) {
            console.error('[UnifiedGeneratorBattle] Error creating battle:', error);
            if (window.showToast) {
                window.showToast('Error creating battle', 'error');
            }
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async completeBattle(battleId, won, duration = 0.0, moves = 0) {
        try {
            console.log('[UnifiedGeneratorBattle] Completing battle...', battleId, won);
            
            const response = await fetch(`${this.BASE_URL}/api/unified/complete-battle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    battle_id: battleId,
                    user_id: this.userId,
                    won: won,
                    duration: duration,
                    moves: moves
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[UnifiedGeneratorBattle] Battle completed:', data);
                
                // Show success notification
                if (window.showToast) {
                    window.showToast(won ? 'Battle won! 🎉' : 'Battle completed', won ? 'success' : 'info');
                }
                
                return data;
            } else {
                console.error('[UnifiedGeneratorBattle] Battle completion failed:', data.error);
                if (window.showToast) {
                    window.showToast(`Battle completion failed: ${data.error}`, 'error');
                }
                return data;
            }
        } catch (error) {
            console.error('[UnifiedGeneratorBattle] Error completing battle:', error);
            if (window.showToast) {
                window.showToast('Error completing battle', 'error');
            }
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async getUnifiedStats() {
        try {
            const response = await fetch(`${this.BASE_URL}/api/unified/stats?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                return data.stats;
            }
        } catch (error) {
            console.error('[UnifiedGeneratorBattle] Error getting stats:', error);
        }
        return null;
    }
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const userId = localStorage.getItem('game_user_id') || 'default_user';
        window.unifiedGeneratorBattle = new UnifiedGeneratorBattle('', userId);
    });
} else {
    const userId = localStorage.getItem('game_user_id') || 'default_user';
    window.unifiedGeneratorBattle = new UnifiedGeneratorBattle('', userId);
}
