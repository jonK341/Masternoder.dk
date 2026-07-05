/**
 * Connect All Point Counters
 * Initializes and connects all point counter systems
 */
(function() {
    'use strict';
    
    console.log('[ConnectAllPointCounters] Initializing...');
    
    function connectAllPointCounters() {
        // Initialize unified point counters if available
        if (typeof window.UnifiedPointCounters !== 'undefined') {
            if (!window.unifiedPointCounters) {
                window.unifiedPointCounters = new window.UnifiedPointCounters();
            }
            
            // Update all counters immediately
            if (window.unifiedPointCounters.updateAllCounters) {
                window.unifiedPointCounters.updateAllCounters();
            }
            
            // Start auto-update if available
            if (window.unifiedPointCounters.startAutoUpdate) {
                window.unifiedPointCounters.startAutoUpdate(30000); // 30 seconds
            }
        }
        
        // Also try to initialize from unified-point-counters.js if it's already loaded
        if (typeof unifiedPointCounters !== 'undefined') {
            if (unifiedPointCounters.updateAllCounters) {
                unifiedPointCounters.updateAllCounters();
            }
            if (unifiedPointCounters.startAutoUpdate) {
                unifiedPointCounters.startAutoUpdate(30000);
            }
        }
        
        console.log('[ConnectAllPointCounters] All point counters connected');
    }
    
    // Connect when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', connectAllPointCounters);
    } else {
        // DOM already ready
        connectAllPointCounters();
    }
    
    // Also connect on window load as backup
    window.addEventListener('load', function() {
        setTimeout(connectAllPointCounters, 500); // Wait a bit for other scripts to load
    });
    
    // Export function for manual calls
    window.connectAllPointCounters = connectAllPointCounters;
    
    console.log('[ConnectAllPointCounters] Module loaded');
})();
