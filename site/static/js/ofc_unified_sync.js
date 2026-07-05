/**
 * OFC Unified Points Sync
 * Synchronizes and equalizes all unified points to frontend UI
 */
class OFCUnifiedSync {
    constructor(baseUrl = window.location.origin) {
        this.baseUrl = baseUrl;
        this.syncInterval = null;
        this.lastSyncTime = null;
    }
    
    async syncAllPoints(userId = 'default') {
        try {
            const response = await fetch(`${this.baseUrl}/api/ofc/unified-points/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.lastSyncTime = new Date();
                
                // Update UI with all points
                this.updateUIWithPoints(result.unified_points, result.matrix, result.calculation);
                
                console.log('[OFC Unified Sync] Points synced successfully:', result);
                return result;
            } else {
                console.error('[OFC Unified Sync] Sync failed:', result.error);
                return result;
            }
        } catch (error) {
            console.error('[OFC Unified Sync] Error syncing points:', error);
            return { success: false, error: error.message };
        }
    }
    
    updateUIWithPoints(unifiedPoints, matrix, calculation) {
        // Update all point counters in UI
        if (window.unifiedPointCounters) {
            window.unifiedPointCounters.updateCountersInDOM(unifiedPoints);
        }
        
        // Update matrix display
        if (matrix) {
            this.updateMatrixDisplay(matrix);
        }
        
        // Update resource generation display
        if (matrix && matrix.resource_generation) {
            this.updateResourceDisplay(matrix.resource_generation);
        }
        
        // Update calculation display
        if (calculation) {
            this.updateCalculationDisplay(calculation);
        }
    }
    
    updateMatrixDisplay(matrix) {
        const matrixElement = document.getElementById('unified-matrix-display');
        if (matrixElement) {
            matrixElement.innerHTML = `
                <div class="matrix-card">
                    <h4>Unified Point Matrix</h4>
                    <div class="matrix-total">${(matrix.unified_total || 0).toLocaleString()}</div>
                    <div class="matrix-breakdown">
                        ${Object.entries(matrix.breakdown || {}).map(([key, value]) => `
                            <div class="matrix-item">
                                <span class="matrix-key">${key}:</span>
                                <span class="matrix-value">${value.toLocaleString()}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    }
    
    updateResourceDisplay(resources) {
        const resourceElement = document.getElementById('resource-generation-display');
        if (resourceElement) {
            resourceElement.innerHTML = `
                <div class="resource-card">
                    <h4>Resource Generation</h4>
                    <div class="resource-grid">
                        ${Object.entries(resources).filter(([key]) => key !== 'future_demand').map(([key, value]) => `
                            <div class="resource-item">
                                <span class="resource-key">${key.replace('_', ' ')}:</span>
                                <span class="resource-value">${typeof value === 'number' ? value.toFixed(2) : value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    }
    
    updateCalculationDisplay(calculation) {
        const calcElement = document.getElementById('calculation-display');
        if (calcElement) {
            calcElement.innerHTML = `
                <div class="calculation-card">
                    <h4>System Calculation</h4>
                    <div class="calc-info">
                        <p>Calculated: ${new Date(calculation.calculated_at).toLocaleString()}</p>
                        <p>Systems: ${calculation.systems_included?.join(', ') || 'N/A'}</p>
                        <p>Unified Total: ${(calculation.unified_total || 0).toLocaleString()}</p>
                    </div>
                </div>
            `;
        }
    }
    
    startAutoSync(userId = 'default', intervalMs = 30000) {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }
        
        // Initial sync
        this.syncAllPoints(userId);
        
        // Auto-sync
        this.syncInterval = setInterval(() => {
            this.syncAllPoints(userId);
        }, intervalMs);
        
        console.log(`[OFC Unified Sync] Auto-sync started (${intervalMs}ms interval)`);
    }
    
    stopAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
            console.log('[OFC Unified Sync] Auto-sync stopped');
        }
    }
    
    async calculateAllNow(userId = 'default') {
        try {
            const response = await fetch(`${this.baseUrl}/api/ofc/unified-matrix/calculate-all`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log('[OFC Unified Sync] All points calculated:', result);
                this.updateCalculationDisplay(result.calculation);
                return result;
            } else {
                console.error('[OFC Unified Sync] Calculation failed:', result.error);
                return result;
            }
        } catch (error) {
            console.error('[OFC Unified Sync] Error calculating all:', error);
            return { success: false, error: error.message };
        }
    }
}

// Global instance
window.ofcUnifiedSync = new OFCUnifiedSync();

// Auto-initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.ofcUnifiedSync.startAutoSync();
    });
} else {
    window.ofcUnifiedSync.startAutoSync();
}

