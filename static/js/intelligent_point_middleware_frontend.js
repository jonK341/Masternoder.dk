/**
 * Intelligent Point Middleware - Frontend
 * Two coupling points on frontend side for maximum stability
 * Handles all point updates with multiple accountability layers
 */
class IntelligentPointMiddlewareFrontend {
    constructor() {
        this.baseUrl = window.location.origin;
        this.couplings = {
            validation: null,
            notification: null
        };
        this.pointLayers = {
            layer1: {}, // Primary layer
            layer2: {}, // Secondary layer
            layer3: {}, // Tertiary layer
            layer4: {}  // Quaternary layer
        };
        this.updateQueue = [];
        this.isProcessing = false;
    }

    /**
     * Register frontend coupling point 1: Validation
     */
    registerValidationCoupling(handler) {
        this.couplings.validation = handler;
        console.log('[Frontend Middleware] Validation coupling registered');
    }

    /**
     * Register frontend coupling point 2: Notification
     */
    registerNotificationCoupling(handler) {
        this.couplings.notification = handler;
        console.log('[Frontend Middleware] Notification coupling registered');
    }

    /**
     * Process point update through all layers
     */
    async processPointUpdate(userId, pointType, amount, metadata = {}) {
        const update = {
            userId,
            pointType,
            amount,
            metadata,
            timestamp: new Date().toISOString(),
            layers: {}
        };

        try {
            // Layer 1: Validation
            update.layers.layer1 = await this._processLayer1(update);
            if (!update.layers.layer1.valid) {
                throw new Error(update.layers.layer1.error || 'Layer 1 validation failed');
            }

            // Layer 2: Calculation
            update.layers.layer2 = await this._processLayer2(update);
            
            // Layer 3: Aggregation
            update.layers.layer3 = await this._processLayer3(update);
            
            // Layer 4: Persistence
            update.layers.layer4 = await this._processLayer4(update);

            // Send to backend through middleware
            const backendResult = await this._sendToBackend(update);
            
            // Notify through coupling 2
            if (this.couplings.notification) {
                this.couplings.notification(update, backendResult);
            }

            return {
                success: true,
                update,
                backendResult
            };
        } catch (error) {
            console.error('[Frontend Middleware] Error processing point update:', error);
            return {
                success: false,
                error: error.message,
                update
            };
        }
    }

    /**
     * Layer 1: Validation
     */
    async _processLayer1(update) {
        const result = {
            layer: 'validation',
            valid: true,
            timestamp: new Date().toISOString()
        };

        // Frontend coupling 1: Validation
        if (this.couplings.validation) {
            const validationResult = this.couplings.validation(
                update.userId,
                update.pointType,
                update.amount,
                update.metadata
            );
            result.valid = validationResult.valid !== false;
            result.details = validationResult;
        }

        // Store in layer 1
        this.pointLayers.layer1[update.pointType] = {
            ...update,
            validated: result.valid
        };

        return result;
    }

    /**
     * Layer 2: Calculation
     */
    async _processLayer2(update) {
        const result = {
            layer: 'calculation',
            originalAmount: update.amount,
            calculatedAmount: update.amount,
            multipliers: [],
            timestamp: new Date().toISOString()
        };

        // Apply multipliers
        let finalAmount = update.amount;

        // Death Portal multiplier (10x)
        if (update.metadata.death_portal) {
            finalAmount *= 10.0;
            result.multipliers.push({ type: 'death_portal', multiplier: 10.0 });
        }

        // Production 10x multiplier
        if (update.metadata.production_10x) {
            finalAmount *= 10.0;
            result.multipliers.push({ type: 'production_10x', multiplier: 10.0 });
        }

        // Tech power multiplier (1.5x)
        if (update.metadata.tech_power) {
            finalAmount *= 1.5;
            result.multipliers.push({ type: 'tech_power', multiplier: 1.5 });
        }

        // Shadows power multiplier (2x)
        if (update.metadata.shadows_power) {
            finalAmount *= 2.0;
            result.multipliers.push({ type: 'shadows_power', multiplier: 2.0 });
        }

        result.calculatedAmount = finalAmount;
        update.amount = finalAmount;

        // Store in layer 2
        this.pointLayers.layer2[update.pointType] = {
            ...update,
            calculation: result
        };

        return result;
    }

    /**
     * Layer 3: Aggregation
     */
    async _processLayer3(update) {
        const result = {
            layer: 'aggregation',
            aggregated: true,
            systems: [],
            timestamp: new Date().toISOString()
        };

        // Determine which systems should receive this update
        const systems = this._determineTargetSystems(update.pointType);
        result.systems = systems;

        // Store in layer 3
        this.pointLayers.layer3[update.pointType] = {
            ...update,
            aggregation: result
        };

        return result;
    }

    /**
     * Layer 4: Persistence
     */
    async _processLayer4(update) {
        const result = {
            layer: 'persistence',
            persisted: false,
            timestamp: new Date().toISOString()
        };

        // Store in layer 4 (local storage for now)
        try {
            const key = `points_${update.userId}_${update.pointType}`;
            const existing = JSON.parse(localStorage.getItem(key) || '{}');
            existing.value = (existing.value || 0) + update.amount;
            existing.lastUpdate = new Date().toISOString();
            localStorage.setItem(key, JSON.stringify(existing));
            result.persisted = true;
        } catch (error) {
            console.warn('[Frontend Middleware] Failed to persist locally:', error);
        }

        // Store in layer 4
        this.pointLayers.layer4[update.pointType] = {
            ...update,
            persistence: result
        };

        return result;
    }

    /**
     * Send to backend through middleware
     */
    async _sendToBackend(update) {
        try {
            const response = await fetch(`${this.baseUrl}/api/points/intelligent-update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: update.userId,
                    point_type: update.pointType,
                    amount: update.amount,
                    metadata: update.metadata,
                    layers: update.layers
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[Frontend Middleware] Backend update failed:', error);
            throw error;
        }
    }

    /**
     * Determine target systems for point update
     */
    _determineTargetSystems(pointType) {
        const systems = [];
        
        // All 178 systems that should receive this point
        // This is a simplified version - full implementation would check all 178
        
        // Core systems always get points
        systems.push('xp', 'activity', 'unified');
        
        // Type-specific systems
        if (pointType.includes('battle')) {
            systems.push('battle', 'pvp_battle', 'pve_battle');
        }
        if (pointType.includes('skill')) {
            systems.push('skills', 'abilities', 'aggregator_resources');
        }
        if (pointType.includes('tech')) {
            systems.push('tech_power');
        }
        if (pointType.includes('shadow')) {
            systems.push('shadows_power', 'secret_resources');
        }
        
        // Special systems
        systems.push('pussyhul_32', 'birthday_rewards');
        
        return systems;
    }

    /**
     * Get all points from all layers
     */
    getAllPoints(userId) {
        const allPoints = {};
        
        // Aggregate from all layers
        for (const layerName in this.pointLayers) {
            const layer = this.pointLayers[layerName];
            for (const pointType in layer) {
                if (!allPoints[pointType]) {
                    allPoints[pointType] = 0;
                }
                allPoints[pointType] += layer[pointType].amount || 0;
            }
        }
        
        return allPoints;
    }

    /**
     * Sync with backend
     */
    async syncWithBackend(userId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/points/sync-all?user_id=${userId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // Update all layers with synced data
            if (data.points) {
                for (const pointType in data.points) {
                    this.pointLayers.layer1[pointType] = {
                        pointType,
                        amount: data.points[pointType],
                        synced: true
                    };
                }
            }
            
            return data;
        } catch (error) {
            console.error('[Frontend Middleware] Sync failed:', error);
            throw error;
        }
    }
}

// Global instance
const intelligentPointMiddlewareFrontend = new IntelligentPointMiddlewareFrontend();

// Register default couplings
intelligentPointMiddlewareFrontend.registerValidationCoupling((userId, pointType, amount, metadata) => {
    // Default validation: check amount is positive
    return {
        valid: amount > 0,
        error: amount <= 0 ? 'Amount must be positive' : null
    };
});

intelligentPointMiddlewareFrontend.registerNotificationCoupling((update, backendResult) => {
    // Default notification: log to console
    console.log('[Point Update]', update.pointType, update.amount, backendResult);
    
    // Update UI if unified counters exist
    if (window.unifiedPointCounters) {
        window.unifiedPointCounters.updateAllCounters();
    }
    
    // Update hypnotic counters if they exist
    if (window.hypnoticPointCounters) {
        window.hypnoticPointCounters.updateAllCounters();
    }
});

// Export
window.IntelligentPointMiddlewareFrontend = IntelligentPointMiddlewareFrontend;
window.intelligentPointMiddlewareFrontend = intelligentPointMiddlewareFrontend;

