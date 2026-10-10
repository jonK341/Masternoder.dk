/**
 * Enhanced Monitor Logic
 * Adds intelligent updates, progress visualization, and user-friendly feedback
 */
class EnhancedMonitorLogic {
    constructor() {
        this.monitor = null;
        this.progressBar = null;
        this.currentProgress = 0;
        this.currentPhase = 'INITIALIZING';
        this.updateInterval = null;
        this.lastUpdateTime = Date.now();
    }

    init() {
        console.log('[EnhancedMonitor] Initializing enhanced monitor logic...');
        
        this.monitor = document.getElementById('matrix-monitor');
        if (!this.monitor) {
            console.warn('[EnhancedMonitor] Monitor element not found');
            return;
        }

        // Create progress bar if it doesn't exist
        this.createProgressBar();
        
        // Enhance existing monitor elements
        this.enhanceMonitorElements();
        
        // Start update loop
        this.startUpdateLoop();
        
        // Listen for progress updates
        this.setupProgressListener();
        
        console.log('[EnhancedMonitor] Enhanced monitor logic initialized');
    }

    createProgressBar() {
        const container = this.monitor.querySelector('.matrix-monitor-container');
        if (!container) return;

        // Check if progress bar already exists
        if (container.querySelector('.monitor-progress-container')) return;

        const progressContainer = document.createElement('div');
        progressContainer.className = 'monitor-progress-container';
        progressContainer.innerHTML = `
            <div class="monitor-progress-label">PROGRESS</div>
            <div class="monitor-progress-bar">
                <div class="monitor-progress-fill" id="monitor-progress-fill" style="width: 0%"></div>
                <div class="monitor-progress-label" id="monitor-progress-text">0%</div>
            </div>
        `;

        // Insert at the beginning of container
        container.insertBefore(progressContainer, container.firstChild);
        
        this.progressBar = document.getElementById('monitor-progress-fill');
    }

    enhanceMonitorElements() {
        // Enhance status text
        const statusText = document.getElementById('monitor-status-text');
        if (statusText) {
            statusText.style.fontWeight = '600';
            statusText.style.textShadow = '0 0 8px rgba(0, 255, 150, 0.6)';
        }

        // Add phase indicators
        this.createPhaseIndicators();
        
        // Enhance stats display
        this.enhanceStatsDisplay();
    }

    createPhaseIndicators() {
        const container = this.monitor.querySelector('.matrix-monitor-container');
        if (!container) return;

        // Check if phase indicators already exist
        if (container.querySelector('.monitor-phases-container')) return;

        const phasesContainer = document.createElement('div');
        phasesContainer.className = 'monitor-phases-container';
        phasesContainer.style.cssText = 'margin: 12px 0; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;';
        
        const phases = [
            'INITIALIZING', 'SCRAPING', 'ANALYZING', 'GENERATING_CLIPS',
            'PROCESSING', 'COMBINING', 'FINALIZING', 'COMPLETE'
        ];

        phases.forEach((phase, index) => {
            const phaseEl = document.createElement('div');
            phaseEl.className = 'monitor-phase-indicator';
            phaseEl.id = `phase-indicator-${index}`;
            phaseEl.textContent = phase;
            phasesContainer.appendChild(phaseEl);
        });

        const monitorText = container.querySelector('#monitor-text');
        if (monitorText && monitorText.parentNode) {
            monitorText.parentNode.insertBefore(phasesContainer, monitorText);
        }
    }

    enhanceStatsDisplay() {
        const statsContainer = this.monitor.querySelector('.monitor-stats-grid');
        if (!statsContainer) {
            // Create stats grid if it doesn't exist
            const container = this.monitor.querySelector('.matrix-monitor-container');
            if (container) {
                const statsGrid = document.createElement('div');
                statsGrid.className = 'monitor-stats-grid';
                statsGrid.id = 'monitor-stats-grid';
                container.appendChild(statsGrid);
            }
        }
    }

    startUpdateLoop() {
        // Update every 500ms for smooth animations
        this.updateInterval = setInterval(() => {
            this.updateMonitor();
        }, 500);
    }

    updateMonitor() {
        // Update progress bar
        if (this.progressBar) {
            const progress = this.getCurrentProgress();
            this.progressBar.style.width = `${progress}%`;
            
            const progressText = document.getElementById('monitor-progress-text');
            if (progressText) {
                progressText.textContent = `${Math.round(progress)}%`;
            }
        }

        // Update phase indicators
        this.updatePhaseIndicators();

        // Update status based on progress
        this.updateStatus();
    }

    getCurrentProgress() {
        // Try to get progress from various sources
        const progressEl = document.querySelector('[data-progress]');
        if (progressEl) {
            const progress = parseInt(progressEl.dataset.progress) || 0;
            return Math.min(100, Math.max(0, progress));
        }

        // Try to parse from monitor text
        const monitorText = document.getElementById('monitor-text');
        if (monitorText) {
            const text = monitorText.textContent;
            const progressMatch = text.match(/(\d+)%/);
            if (progressMatch) {
                return parseInt(progressMatch[1]);
            }
        }

        return this.currentProgress;
    }

    updatePhaseIndicators() {
        const progress = this.getCurrentProgress();
        const phase = this.getPhaseFromProgress(progress);

        // Update all phase indicators
        const indicators = document.querySelectorAll('.monitor-phase-indicator');
        indicators.forEach((indicator, index) => {
            const phaseName = indicator.textContent;
            if (phaseName === phase) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    }

    getPhaseFromProgress(progress) {
        if (progress < 5) return 'INITIALIZING';
        if (progress < 20) return 'SCRAPING';
        if (progress < 40) return 'ANALYZING';
        if (progress < 60) return 'GENERATING_CLIPS';
        if (progress < 75) return 'PROCESSING';
        if (progress < 90) return 'COMBINING';
        if (progress < 100) return 'FINALIZING';
        return 'COMPLETE';
    }

    updateStatus() {
        const progress = this.getCurrentProgress();
        const statusText = document.getElementById('monitor-status-text');
        const statusBlink = this.monitor.querySelector('.matrix-blink');
        
        if (!statusText || !statusBlink) return;

        // Remove all status classes
        this.monitor.classList.remove('success', 'error', 'warning');

        if (progress >= 100) {
            statusText.textContent = 'COMPLETE';
            statusBlink.style.background = '#00ff96';
            this.monitor.classList.add('success');
        } else if (progress > 0) {
            statusText.textContent = 'PROCESSING';
            statusBlink.style.background = '#00ff96';
        } else {
            statusText.textContent = 'STANDBY';
            statusBlink.style.background = 'rgba(0, 255, 150, 0.5)';
        }
    }

    setupProgressListener() {
        // Listen for custom progress events
        window.addEventListener('progressUpdate', (event) => {
            if (event.detail && event.detail.progress !== undefined) {
                this.currentProgress = event.detail.progress;
                this.currentPhase = event.detail.phase || this.getPhaseFromProgress(this.currentProgress);
                
                // Update progress bar immediately
                if (this.progressBar) {
                    this.progressBar.style.width = `${this.currentProgress}%`;
                }
                
                // Update status
                this.updateStatus();
                this.updatePhaseIndicators();
            }
        });

        // Listen for generation completion
        window.addEventListener('generationCompleted', () => {
            this.currentProgress = 100;
            this.currentPhase = 'COMPLETE';
            this.updateStatus();
            this.updatePhaseIndicators();
        });
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const enhancedMonitor = new EnhancedMonitorLogic();
        enhancedMonitor.init();
        window.enhancedMonitor = enhancedMonitor; // Make it accessible globally
    });
} else {
    const enhancedMonitor = new EnhancedMonitorLogic();
    enhancedMonitor.init();
    window.enhancedMonitor = enhancedMonitor;
}

