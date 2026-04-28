/**
 * Trigger-Based Actions System
 * Converts instant generator/battle to trigger-based behavior with pointer catching
 */

class TriggerBasedActions {
    constructor() {
        this.baseURL = '/api';
        this.userId = this.getUserId();
        this.activeTriggers = new Map();
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        return 'default_user';
    }

    /**
     * Register a trigger for generator or battle
     */
    async registerTrigger(triggerType, data, expectedPointers = []) {
        try {
            const response = await fetch(`${this.baseURL}/trigger/register`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    trigger_type: triggerType,
                    trigger_data: data,
                    expected_pointers: expectedPointers
                })
            });

            if (!response.ok) return null;
            const result = await response.json();
            if (result.success) {
                this.activeTriggers.set(result.trigger_id, {
                    type: triggerType,
                    data: data,
                    expected: expectedPointers,
                    received: []
                });
                return result.trigger_id;
            }
            return null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Catch a pointer and check for matching triggers
     */
    async catchPointer(pointerId, pointerData = {}) {
        try {
            const response = await fetch(`${this.baseURL}/trigger/pointer`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    pointer_id: pointerId,
                    pointer_data: pointerData
                })
            });

            const result = await response.json();
            if (result.success && result.triggers_activated.length > 0) {
                // Triggers were activated
                for (const triggerId of result.triggers_activated) {
                    this.handleTriggerActivation(triggerId);
                }
            }
            return result;
        } catch (error) {
            console.error('Error catching pointer:', error);
            return {success: false, error: error.message};
        }
    }

    /**
     * Handle trigger activation
     */
    async handleTriggerActivation(triggerId) {
        const trigger = this.activeTriggers.get(triggerId);
        if (!trigger) return;

        // Get trigger status
        const status = await this.getTriggerStatus(triggerId);
        if (status && status.trigger.status === 'completed') {
            // Execute the action
            if (trigger.type === 'video_generation') {
                this.executeVideoGeneration(trigger.data, status.trigger.result);
            } else if (trigger.type === 'quick_battle') {
                this.executeQuickBattle(trigger.data, status.trigger.result);
            }
            
            // Remove from active triggers
            this.activeTriggers.delete(triggerId);
        }
    }

    /**
     * Get trigger status
     */
    async getTriggerStatus(triggerId) {
        try {
            const response = await fetch(`${this.baseURL}/trigger/status/${triggerId}`);
            return await response.json();
        } catch (error) {
            console.error('Error getting trigger status:', error);
            return null;
        }
    }

    /**
     * Trigger-based video generation (not instant)
     */
    async triggerVideoGeneration(prompt, options = {}) {
        // Register trigger
        const expectedPointers = [
            'energy_sufficient',
            'points_available',
            'generation_ready'
        ];

        const triggerId = await this.registerTrigger('video_generation', {
            user_id: this.userId,
            prompt: prompt,
            ...options
        }, expectedPointers);

        if (!triggerId) {
            return {success: false, error: 'Failed to register trigger'};
        }

        // Check energy (pointer 1)
        const energy = await this.checkEnergy();
        if (energy.success && energy.energy.total_energy > 50) {
            await this.catchPointer('energy_sufficient', {energy: energy.energy});
        }

        // Check points (pointer 2)
        const points = await this.checkPoints();
        if (points.success && points.points.total > 0) {
            await this.catchPointer('points_available', {points: points.points});
        }

        // Check generation ready (pointer 3)
        const ready = await this.checkGenerationReady();
        if (ready.success && ready.ready) {
            await this.catchPointer('generation_ready', {ready: true});
        }

        return {
            success: true,
            trigger_id: triggerId,
            message: 'Generation trigger registered. Waiting for all pointers...'
        };
    }

    /**
     * Trigger-based quick battle (not instant)
     */
    async triggerQuickBattle(battleType = 'quick', options = {}) {
        // Register trigger
        const expectedPointers = [
            'energy_check',
            'points_available',
            'battle_ready'
        ];

        const triggerId = await this.registerTrigger('quick_battle', {
            user_id: this.userId,
            battle_type: battleType,
            ...options
        }, expectedPointers);

        if (!triggerId) {
            return {success: false, error: 'Failed to register trigger'};
        }

        // Check energy (pointer 1)
        const energy = await this.checkEnergy();
        if (energy.success) {
            await this.catchPointer('energy_check', {energy: energy.energy});
        }

        // Check points (pointer 2)
        const points = await this.checkPoints();
        if (points.success && points.points.total > 0) {
            await this.catchPointer('points_available', {points: points.points});
        }

        // Check battle ready (pointer 3)
        const ready = await this.checkBattleReady();
        if (ready.success && ready.ready) {
            await this.catchPointer('battle_ready', {ready: true});
        }

        return {
            success: true,
            trigger_id: triggerId,
            message: 'Battle trigger registered. Waiting for all pointers...'
        };
    }

    /**
     * Check energy status
     */
    async checkEnergy() {
        try {
            const response = await fetch(`/api/ultra-resource/energy?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Check points availability
     */
    async checkPoints() {
        try {
            const response = await fetch(`/api/points/unified/get?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Check if generation is ready
     */
    async checkGenerationReady() {
        // Check if generator system is ready
        return {success: true, ready: true};
    }

    /**
     * Check if battle is ready
     */
    async checkBattleReady() {
        // Check if battle system is ready
        return {success: true, ready: true};
    }

    /**
     * Execute video generation after trigger activation
     */
    async executeVideoGeneration(data, result) {
        if (window.showToast) {
            window.showToast('All pointers received! Starting generation...', 'success');
        }
        
        // Now execute the actual generation
        if (window.generateVideo) {
            window.generateVideo(data.prompt, data);
        }
    }

    /**
     * Execute quick battle after trigger activation
     */
    async executeQuickBattle(data, result) {
        if (window.showToast) {
            window.showToast('All pointers received! Starting battle...', 'success');
        }
        
        // Now execute the actual battle
        if (window.quickBattleTerritoryExpansion) {
            window.quickBattleTerritoryExpansion();
        }
    }

    /**
     * Award energy points
     */
    async awardEnergyPoints(energyType, amount, source = 'general') {
        try {
            const response = await fetch(`${this.baseURL}/points/energy/award`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    energy_type: energyType,
                    amount: amount,
                    source: source
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Award function points
     */
    async awardFunctionPoints(functionType, amount) {
        try {
            const response = await fetch(`${this.baseURL}/points/function/award`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    function_type: functionType,
                    amount: amount
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get unified points and energy (canonical endpoint: /api/points/all)
     */
    async getUnifiedPoints() {
        try {
            const response = await fetch(`/api/points/all?user_id=${encodeURIComponent(this.userId)}`);
            const data = await response.json();
            if (!data || !response.ok) return { success: false, points: {}, energy: {} };
            return { success: !!data.success, user_id: data.user_id, points: data.points || {}, energy: {} };
        } catch (error) {
            return { success: false, points: {}, energy: {} };
        }
    }
}

// Global instance
window.triggerBasedActions = new TriggerBasedActions();

// Replace instant functions with trigger-based
if (typeof window !== 'undefined') {
    // Override generateVideo if exists
    const originalGenerateVideo = window.generateVideo;
    window.generateVideo = function(prompt, options) {
        if (window.triggerBasedActions) {
            return window.triggerBasedActions.triggerVideoGeneration(prompt, options);
        } else if (originalGenerateVideo) {
            return originalGenerateVideo(prompt, options);
        }
    };

    // Override quickBattle if exists
    const originalQuickBattle = window.quickBattleTerritoryExpansion;
    window.quickBattleTerritoryExpansion = function() {
        if (window.triggerBasedActions) {
            return window.triggerBasedActions.triggerQuickBattle('quick');
        } else if (originalQuickBattle) {
            return originalQuickBattle();
        }
    };
}

