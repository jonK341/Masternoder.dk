/* Monitor Stats Tabs - Tab Switching Functionality */
(function() {
    'use strict';
    
    // Initialize tabs when DOM is ready
    function initMonitorTabs() {
        const tabButtons = document.querySelectorAll('.monitor-tab-btn');
        const tabContents = document.querySelectorAll('.monitor-tab-content');
        
        if (tabButtons.length === 0 || tabContents.length === 0) {
            return; // Tabs not found, skip initialization
        }
        
        // Tab switching function
        function switchTab(tabName) {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to selected button and content
            const selectedBtn = document.querySelector(`.monitor-tab-btn[data-tab="${tabName}"]`);
            const selectedContent = document.getElementById(`tab-${tabName}`);
            
            if (selectedBtn && selectedContent) {
                selectedBtn.classList.add('active');
                selectedContent.classList.add('active');
                
                // Store last active tab in localStorage
                try {
                    localStorage.setItem('monitor-active-tab', tabName);
                } catch (e) {
                    // Ignore localStorage errors
                }
            }
        }
        
        // Add click handlers to tab buttons
        tabButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                if (tabName) {
                    switchTab(tabName);
                }
            });
        });
        
        // Restore last active tab from localStorage
        try {
            const lastTab = localStorage.getItem('monitor-active-tab');
            if (lastTab) {
                switchTab(lastTab);
            }
        } catch (e) {
            // Ignore localStorage errors, use default
        }
        
        // Sync stat updates across tabs (update all instances of same stat)
        function syncStatUpdates() {
            // Find all elements with same ID and update them
            const statIds = [
                'monitor-current-phase',
                'monitor-phase-progress',
                'monitor-phase-elapsed',
                'monitor-phase-eta',
                'monitor-total-clips',
                'monitor-total-duration',
                'monitor-total-size'
            ];
            
            statIds.forEach(id => {
                const elements = document.querySelectorAll(`#${id}, #${id}-gen, #${id}-clips`);
                if (elements.length > 1) {
                    // If multiple elements exist, sync their values
                    let lastValue = null;
                    elements.forEach(el => {
                        if (el.textContent && el.textContent !== '--' && el.textContent !== '0') {
                            lastValue = el.textContent;
                        }
                    });
                    if (lastValue) {
                        elements.forEach(el => {
                            if (!el.textContent || el.textContent === '--' || el.textContent === '0') {
                                el.textContent = lastValue;
                            }
                        });
                    }
                }
            });
        }
        
        // Sync stats periodically
        setInterval(syncStatUpdates, 1000);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMonitorTabs);
    } else {
        initMonitorTabs();
    }
    
    // Re-initialize if content is dynamically loaded
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    const hasTabs = Array.from(mutation.addedNodes).some(node => {
                        return node.nodeType === 1 && (
                            node.classList?.contains('monitor-stats-tabs') ||
                            node.querySelector?.('.monitor-stats-tabs')
                        );
                    });
                    if (hasTabs) {
                        initMonitorTabs();
                    }
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
})();

