/**
 * Hypnotic Point Counters - Enhanced with Mesmerizing Visual Effects
 * Creates engaging, attention-grabbing point displays with hypnotic animations
 */
class HypnoticPointCounters {
    constructor() {
        this.baseUrl = window.location.origin;
        this.cache = {};
        this.cacheTimeout = 30000;
        this.updateInterval = null;
        this.animationFrame = null;
        this.particles = [];
        this.initParticles();
    }

    /**
     * Initialize particle system for hypnotic effects
     */
    initParticles() {
        for (let i = 0; i < 50; i++) {
            this.particles.push({
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 3 + 1,
                opacity: Math.random() * 0.5 + 0.2,
                hue: Math.random() * 360
            });
        }
    }

    /**
     * Load all points from unified endpoint
     */
    async loadAllPoints(forceRefresh = false) {
        try {
            const cacheKey = 'unified_points';
            const cached = this.cache[cacheKey];
            
            if (!forceRefresh && cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
                return cached.data;
            }

            const response = await fetch(`${this.baseUrl}/api/points/all?refresh=${forceRefresh}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.success && data.points) {
                this.cache[cacheKey] = {
                    data: data.points,
                    timestamp: Date.now()
                };
                return data.points;
            }
            throw new Error('Invalid response format');
        } catch (error) {
            console.error('[HypnoticPointCounters] Error loading points:', error);
            return this.getDefaultPoints();
        }
    }

    getDefaultPoints() {
        return {
            xp_total: 0, level: 1, stats_points_total: 0,
            achievements_earned: 0, coins: 0, credits: 0,
            accuracy_grade: 'A+'
        };
    }

    /**
     * Create or update hypnotic point counter widget
     */
    createHypnoticWidget(points) {
        let widget = document.getElementById('hypnotic-points-widget');
        
        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'hypnotic-points-widget';
            widget.className = 'hypnotic-points-widget';
            document.body.appendChild(widget);
            this.injectHypnoticStyles();
        }

        // Create particle canvas
        this.createParticleCanvas(widget);

        // Update widget content
        widget.innerHTML = `
            <div class="hypnotic-widget-content">
                <div class="hypnotic-header">
                    <div class="hypnotic-logo">✨</div>
                    <h3 class="hypnotic-title">Progress Points</h3>
                    <div class="hypnotic-pulse"></div>
                </div>
                
                <div class="hypnotic-stats-grid">
                    <div class="hypnotic-stat-card" data-stat="xp">
                        <div class="stat-icon">⭐</div>
                        <div class="stat-label">XP</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-xp">${this.formatNumber(points.xp_total || 0)}</div>
                        <div class="stat-progress">
                            <div class="progress-bar-hypnotic" id="hypnotic-xp-progress"></div>
                        </div>
                    </div>
                    
                    <div class="hypnotic-stat-card" data-stat="level">
                        <div class="stat-icon">🎯</div>
                        <div class="stat-label">Level</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-level">${points.level || 1}</div>
                        <div class="stat-glow"></div>
                    </div>
                    
                    <div class="hypnotic-stat-card" data-stat="points">
                        <div class="stat-icon">💎</div>
                        <div class="stat-label">Points</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-points">${this.formatNumber(points.stats_points_total || 0)}</div>
                        <div class="stat-sparkle"></div>
                    </div>
                    
                    <div class="hypnotic-stat-card" data-stat="achievements">
                        <div class="stat-icon">🏆</div>
                        <div class="stat-label">Achievements</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-achievements">${points.achievements_earned || 0}</div>
                        <div class="stat-pulse"></div>
                    </div>
                    
                    <div class="hypnotic-stat-card" data-stat="coins">
                        <div class="stat-icon">🪙</div>
                        <div class="stat-label">Coins</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-coins">${this.formatNumber(points.coins || 0)}</div>
                        <div class="stat-rotate"></div>
                    </div>
                    
                    <div class="hypnotic-stat-card" data-stat="credits">
                        <div class="stat-icon">💳</div>
                        <div class="stat-label">Credits</div>
                        <div class="stat-value hypnotic-number" id="hypnotic-credits">${this.formatNumber(points.credits || 0)}</div>
                        <div class="stat-wave"></div>
                    </div>
                </div>
                
                <div class="hypnotic-footer">
                    <div class="accuracy-badge">Accuracy: ${points.accuracy_grade || 'A+'}</div>
                </div>
            </div>
        `;

        // Animate numbers
        this.animateNumbers(points);
        this.updateProgressBars(points);
        this.startParticleAnimation();
    }

    /**
     * Inject hypnotic CSS styles
     */
    injectHypnoticStyles() {
        if (document.getElementById('hypnotic-styles')) return;

        const style = document.createElement('style');
        style.id = 'hypnotic-styles';
        style.textContent = `
            .hypnotic-points-widget {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 350px;
                background: linear-gradient(135deg, rgba(0, 0, 0, 0.95), rgba(20, 10, 40, 0.95));
                border: 2px solid transparent;
                border-radius: 20px;
                padding: 20px;
                z-index: 10000;
                box-shadow: 0 0 50px rgba(100, 50, 200, 0.5),
                            0 0 100px rgba(50, 150, 255, 0.3),
                            inset 0 0 50px rgba(255, 100, 255, 0.1);
                backdrop-filter: blur(10px);
                animation: hypnotic-float 6s ease-in-out infinite;
                overflow: hidden;
            }

            @keyframes hypnotic-float {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-10px) rotate(1deg); }
            }

            .hypnotic-widget-content {
                position: relative;
                z-index: 2;
            }

            .hypnotic-header {
                text-align: center;
                margin-bottom: 20px;
                position: relative;
            }

            .hypnotic-logo {
                font-size: 2em;
                animation: hypnotic-spin 3s linear infinite;
                display: inline-block;
            }

            @keyframes hypnotic-spin {
                0% { transform: rotate(0deg) scale(1); }
                50% { transform: rotate(180deg) scale(1.2); }
                100% { transform: rotate(360deg) scale(1); }
            }

            .hypnotic-title {
                color: #fff;
                margin: 10px 0;
                font-size: 1.3em;
                text-shadow: 0 0 20px rgba(255, 100, 255, 0.8),
                            0 0 40px rgba(100, 150, 255, 0.6);
                animation: hypnotic-glow 2s ease-in-out infinite;
            }

            @keyframes hypnotic-glow {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.8; }
            }

            .hypnotic-pulse {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 200px;
                height: 200px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(255, 100, 255, 0.3), transparent);
                animation: hypnotic-pulse-ring 2s ease-out infinite;
                pointer-events: none;
            }

            @keyframes hypnotic-pulse-ring {
                0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
                100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
            }

            .hypnotic-stats-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 15px;
            }

            .hypnotic-stat-card {
                background: linear-gradient(135deg, rgba(50, 20, 80, 0.6), rgba(20, 50, 100, 0.6));
                border: 1px solid rgba(255, 100, 255, 0.3);
                border-radius: 15px;
                padding: 15px;
                text-align: center;
                position: relative;
                overflow: hidden;
                transition: all 0.3s;
                animation: hypnotic-card-float 4s ease-in-out infinite;
            }

            .hypnotic-stat-card:nth-child(odd) {
                animation-delay: 0s;
            }

            .hypnotic-stat-card:nth-child(even) {
                animation-delay: 2s;
            }

            @keyframes hypnotic-card-float {
                0%, 100% { transform: translateY(0) scale(1); }
                50% { transform: translateY(-5px) scale(1.02); }
            }

            .hypnotic-stat-card:hover {
                transform: scale(1.1) translateY(-5px);
                box-shadow: 0 0 30px rgba(255, 100, 255, 0.6),
                           0 0 60px rgba(100, 150, 255, 0.4);
                border-color: rgba(255, 100, 255, 0.8);
            }

            .stat-icon {
                font-size: 2em;
                margin-bottom: 5px;
                animation: hypnotic-icon-bounce 2s ease-in-out infinite;
            }

            @keyframes hypnotic-icon-bounce {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-5px) rotate(10deg); }
            }

            .stat-label {
                color: #aaa;
                font-size: 0.9em;
                margin-bottom: 5px;
            }

            .hypnotic-number {
                font-size: 1.8em;
                font-weight: bold;
                color: #fff;
                text-shadow: 0 0 10px rgba(255, 100, 255, 0.8),
                            0 0 20px rgba(100, 150, 255, 0.6);
                animation: hypnotic-number-pulse 1.5s ease-in-out infinite;
            }

            @keyframes hypnotic-number-pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }

            .stat-progress {
                margin-top: 10px;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                overflow: hidden;
            }

            .progress-bar-hypnotic {
                height: 100%;
                background: linear-gradient(90deg, 
                    rgba(255, 100, 255, 0.8),
                    rgba(100, 150, 255, 0.8),
                    rgba(255, 100, 255, 0.8));
                background-size: 200% 100%;
                animation: hypnotic-progress-flow 2s linear infinite;
                border-radius: 2px;
            }

            @keyframes hypnotic-progress-flow {
                0% { background-position: 0% 50%; }
                100% { background-position: 200% 50%; }
            }

            .stat-glow, .stat-sparkle, .stat-pulse, .stat-rotate, .stat-wave {
                position: absolute;
                pointer-events: none;
            }

            .stat-glow {
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255, 100, 255, 0.2), transparent);
                animation: hypnotic-glow-rotate 3s linear infinite;
            }

            @keyframes hypnotic-glow-rotate {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .stat-sparkle {
                width: 100%;
                height: 100%;
                background-image: 
                    radial-gradient(2px 2px at 20% 30%, rgba(255, 255, 255, 0.8), transparent),
                    radial-gradient(2px 2px at 60% 70%, rgba(255, 100, 255, 0.8), transparent),
                    radial-gradient(1px 1px at 50% 50%, rgba(255, 255, 255, 0.6), transparent);
                background-size: 200% 200%;
                animation: hypnotic-sparkle 3s linear infinite;
            }

            @keyframes hypnotic-sparkle {
                0% { background-position: 0% 0%; }
                100% { background-position: 200% 200%; }
            }

            .stat-pulse {
                width: 100%;
                height: 100%;
                border-radius: 15px;
                background: rgba(255, 100, 255, 0.2);
                animation: hypnotic-pulse 2s ease-in-out infinite;
            }

            @keyframes hypnotic-pulse {
                0%, 100% { opacity: 0.3; transform: scale(1); }
                50% { opacity: 0.6; transform: scale(1.1); }
            }

            .stat-rotate {
                width: 100%;
                height: 100%;
                background: conic-gradient(
                    rgba(255, 100, 255, 0.3),
                    rgba(100, 150, 255, 0.3),
                    rgba(255, 100, 255, 0.3)
                );
                animation: hypnotic-rotate 4s linear infinite;
            }

            @keyframes hypnotic-rotate {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .stat-wave {
                width: 100%;
                height: 100%;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(100, 150, 255, 0.3),
                    transparent
                );
                background-size: 200% 100%;
                animation: hypnotic-wave 2s ease-in-out infinite;
            }

            @keyframes hypnotic-wave {
                0%, 100% { background-position: -200% 0; }
                50% { background-position: 200% 0; }
            }

            .hypnotic-footer {
                text-align: center;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }

            .accuracy-badge {
                display: inline-block;
                padding: 5px 15px;
                background: linear-gradient(135deg, rgba(0, 255, 136, 0.3), rgba(0, 212, 255, 0.3));
                border: 1px solid rgba(0, 255, 136, 0.5);
                border-radius: 15px;
                color: #00ff88;
                font-size: 0.85em;
                font-weight: bold;
                animation: hypnotic-badge-glow 2s ease-in-out infinite;
            }

            @keyframes hypnotic-badge-glow {
                0%, 100% { box-shadow: 0 0 10px rgba(0, 255, 136, 0.5); }
                50% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.8); }
            }

            .hypnotic-particle-canvas {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 1;
                opacity: 0.3;
            }

            @media (max-width: 768px) {
                .hypnotic-points-widget {
                    position: relative;
                    top: auto;
                    right: auto;
                    width: 100%;
                    margin: 10px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Create particle canvas for background effects
     */
    createParticleCanvas(widget) {
        let canvas = document.getElementById('hypnotic-particles');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.id = 'hypnotic-particles';
            canvas.className = 'hypnotic-particle-canvas';
            widget.appendChild(canvas);
        }
        canvas.width = widget.offsetWidth;
        canvas.height = widget.offsetHeight;
    }

    /**
     * Start particle animation
     */
    startParticleAnimation() {
        const canvas = document.getElementById('hypnotic-particles');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const widget = document.getElementById('hypnotic-points-widget');
        
        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            this.particles.forEach(particle => {
                particle.x += particle.vx;
                particle.y += particle.vy;
                particle.hue = (particle.hue + 1) % 360;
                
                if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
                if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
                
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
                ctx.fillStyle = `hsla(${particle.hue}, 70%, 60%, ${particle.opacity})`;
                ctx.fill();
            });
            
            this.animationFrame = requestAnimationFrame(animate);
        };
        
        animate();
    }

    /**
     * Animate number changes
     */
    animateNumbers(points) {
        const animations = [
            { id: 'hypnotic-xp', value: points.xp_total || 0 },
            { id: 'hypnotic-level', value: points.level || 1 },
            { id: 'hypnotic-points', value: points.stats_points_total || 0 },
            { id: 'hypnotic-achievements', value: points.achievements_earned || 0 },
            { id: 'hypnotic-coins', value: points.coins || 0 },
            { id: 'hypnotic-credits', value: points.credits || 0 }
        ];

        animations.forEach(({ id, value }) => {
            const element = document.getElementById(id);
            if (!element) return;

            const current = parseInt(element.textContent.replace(/,/g, '')) || 0;
            if (current === value) return;

            // Animate with spring effect
            let currentValue = current;
            const target = value;
            const diff = target - current;
            const steps = 30;
            let step = 0;

            const animate = () => {
                step++;
                const progress = step / steps;
                const ease = 1 - Math.pow(1 - progress, 3); // Ease out cubic
                currentValue = Math.round(current + diff * ease);
                
                element.textContent = this.formatNumber(currentValue);
                element.style.transform = `scale(${1 + Math.sin(progress * Math.PI) * 0.2})`;
                
                if (step < steps) {
                    requestAnimationFrame(animate);
                } else {
                    element.style.transform = 'scale(1)';
                }
            };
            
            animate();
        });
    }

    /**
     * Update progress bars
     */
    updateProgressBars(points) {
        const level = points.level || 1;
        const xpTotal = points.xp_total || 0;
        const xpForCurrentLevel = level * 1000;
        const xpForNextLevel = (level + 1) * 1000;
        const xpInLevel = Math.max(0, xpTotal - xpForCurrentLevel);
        const xpNeeded = xpForNextLevel - xpForCurrentLevel;
        const progress = Math.min(100, Math.max(0, (xpInLevel / xpNeeded) * 100));

        const progressBar = document.getElementById('hypnotic-xp-progress');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    /**
     * Format number with commas
     */
    formatNumber(num) {
        return num.toLocaleString();
    }

    /**
     * Update all counters
     */
    async updateAllCounters() {
        const points = await this.loadAllPoints();
        this.createHypnoticWidget(points);
        return points;
    }

    /**
     * Start auto-update
     */
    startAutoUpdate(intervalMs = 30000) {
        if (this.updateInterval) clearInterval(this.updateInterval);
        this.updateInterval = setInterval(() => {
            this.updateAllCounters();
        }, intervalMs);
    }

    /**
     * Stop auto-update
     */
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }
}

// Global instance
const hypnoticPointCounters = new HypnoticPointCounters();

// Auto-initialize (skip on pages that opt out — e.g. home uses this later)
function _mnHypnoticShouldInit() {
    try {
        if (document.body && document.body.classList.contains('mn-no-hypnotic')) return false;
    } catch (_) {}
    return true;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!_mnHypnoticShouldInit()) return;
        hypnoticPointCounters.updateAllCounters();
        hypnoticPointCounters.startAutoUpdate();
    });
} else {
    if (_mnHypnoticShouldInit()) {
        hypnoticPointCounters.updateAllCounters();
        hypnoticPointCounters.startAutoUpdate();
    }
}

// Export
window.HypnoticPointCounters = HypnoticPointCounters;
window.hypnoticPointCounters = hypnoticPointCounters;

