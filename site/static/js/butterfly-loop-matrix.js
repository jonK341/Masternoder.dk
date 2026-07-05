/**
 * Butterfly Loop Matrix - Hypnotic Attraction System
 * Infiltrates user behavior patterns through visual attraction
 */
class ButterflyLoopMatrix {
    constructor(containerId) {
        this.container = document.getElementById(containerId) || document.body;
        this.patterns = [];
        this.behaviorTracker = {
            mouseMovements: [],
            clicks: [],
            scrolls: [],
            timeOnElements: {},
            attentionZones: []
        };
        this.attractionLoops = [];
        this.isActive = false;
    }
    
    init() {
        this.createHypnoticPatterns();
        this.startBehaviorTracking();
        this.initializeAttractionLoops();
        this.isActive = true;
    }
    
    createHypnoticPatterns() {
        // Create spiral patterns
        this.createSpiralPatterns();
        
        // Create rotating mandalas
        this.createRotatingMandalas();
        
        // Create pulsing circles
        this.createPulsingCircles();
        
        // Create color-shifting gradients
        this.createColorShiftingGradients();
    }
    
    createSpiralPatterns() {
        const spiralContainer = document.createElement('div');
        spiralContainer.className = 'butterfly-spiral-container';
        spiralContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
            opacity: 0.15;
        `;
        
        // Create multiple spirals
        for (let i = 0; i < 5; i++) {
            const spiral = document.createElement('div');
            spiral.className = 'butterfly-spiral';
            const size = 200 + Math.random() * 300;
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const rotationSpeed = 10 + Math.random() * 20;
            const direction = Math.random() > 0.5 ? 1 : -1;
            
            spiral.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${left}%;
                top: ${top}%;
                border: 2px solid rgba(0, 255, 136, 0.3);
                border-radius: 50%;
                background: conic-gradient(
                    from 0deg,
                    rgba(0, 255, 136, 0.1),
                    rgba(0, 212, 255, 0.1),
                    rgba(255, 100, 255, 0.1),
                    rgba(0, 255, 136, 0.1)
                );
                animation: spiralRotate${i} ${rotationSpeed}s linear infinite;
                transform-origin: center;
            `;
            
            // Add spiral animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spiralRotate${i} {
                    0% { transform: rotate(0deg) scale(1); }
                    50% { transform: rotate(${180 * direction}deg) scale(1.2); }
                    100% { transform: rotate(${360 * direction}deg) scale(1); }
                }
            `;
            document.head.appendChild(style);
            
            spiralContainer.appendChild(spiral);
        }
        
        this.container.appendChild(spiralContainer);
    }
    
    createRotatingMandalas() {
        const mandalaContainer = document.createElement('div');
        mandalaContainer.className = 'butterfly-mandala-container';
        mandalaContainer.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            z-index: 1;
            opacity: 0.1;
        `;
        
        // Create mandala pattern
        for (let i = 0; i < 8; i++) {
            const petal = document.createElement('div');
            petal.className = 'butterfly-mandala-petal';
            const angle = (i * 45);
            const size = 150;
            
            petal.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: linear-gradient(135deg, 
                    rgba(0, 255, 136, 0.2),
                    rgba(0, 212, 255, 0.2)
                );
                border-radius: 50% 0 50% 0;
                transform: rotate(${angle}deg) translateY(-${size/2}px);
                transform-origin: center;
                animation: mandalaRotate 20s linear infinite;
            `;
            
            mandalaContainer.appendChild(petal);
        }
        
        // Add rotation animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes mandalaRotate {
                0% { transform: translate(-50%, -50%) rotate(0deg); }
                100% { transform: translate(-50%, -50%) rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        this.container.appendChild(mandalaContainer);
    }
    
    createPulsingCircles() {
        const circleContainer = document.createElement('div');
        circleContainer.className = 'butterfly-circle-container';
        circleContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            pointer-events: none;
            z-index: 1;
            opacity: 0.2;
        `;
        
        // Create concentric pulsing circles
        for (let i = 0; i < 3; i++) {
            const circle = document.createElement('div');
            circle.className = 'butterfly-pulse-circle';
            const size = 100 + (i * 50);
            const delay = i * 0.5;
            const duration = 3 + (i * 0.5);
            
            circle.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                border: 3px solid rgba(0, 255, 136, 0.4);
                border-radius: 50%;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                animation: pulseCircle${i} ${duration}s ease-in-out infinite;
                animation-delay: ${delay}s;
            `;
            
            // Add pulse animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes pulseCircle${i} {
                    0%, 100% { 
                        transform: translate(-50%, -50%) scale(1);
                        opacity: 0.4;
                    }
                    50% { 
                        transform: translate(-50%, -50%) scale(1.5);
                        opacity: 0.1;
                    }
                }
            `;
            document.head.appendChild(style);
            
            circleContainer.appendChild(circle);
        }
        
        this.container.appendChild(circleContainer);
    }
    
    createColorShiftingGradients() {
        const gradientOverlay = document.createElement('div');
        gradientOverlay.className = 'butterfly-gradient-overlay';
        gradientOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.05;
            background: linear-gradient(
                135deg,
                rgba(0, 255, 136, 0.3),
                rgba(0, 212, 255, 0.3),
                rgba(255, 100, 255, 0.3),
                rgba(0, 255, 136, 0.3)
            );
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
        `;
        
        // Add gradient animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes gradientShift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
        `;
        document.head.appendChild(style);
        
        this.container.appendChild(gradientOverlay);
    }
    
    startBehaviorTracking() {
        // Track mouse movements
        document.addEventListener('mousemove', (e) => {
            this.behaviorTracker.mouseMovements.push({
                x: e.clientX,
                y: e.clientY,
                timestamp: Date.now()
            });
            
            // Keep only last 100 movements
            if (this.behaviorTracker.mouseMovements.length > 100) {
                this.behaviorTracker.mouseMovements.shift();
            }
            
            // Detect attention zones
            this.detectAttentionZone(e.clientX, e.clientY);
        });
        
        // Track clicks
        document.addEventListener('click', (e) => {
            this.behaviorTracker.clicks.push({
                x: e.clientX,
                y: e.clientY,
                target: e.target.className,
                timestamp: Date.now()
            });
            
            // Trigger attraction response
            this.triggerAttractionResponse(e.clientX, e.clientY);
        });
        
        // Track scrolls
        let scrollTimeout;
        document.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                this.behaviorTracker.scrolls.push({
                    scrollY: window.scrollY,
                    timestamp: Date.now()
                });
            }, 100);
        });
        
        // Track time on elements
        this.trackElementHover();
    }
    
    detectAttentionZone(x, y) {
        // Check if mouse is in an attention zone
        const zoneSize = 100;
        const zones = this.behaviorTracker.attentionZones;
        
        // Find or create zone
        let zone = zones.find(z => 
            Math.abs(z.x - x) < zoneSize && Math.abs(z.y - y) < zoneSize
        );
        
        if (!zone) {
            zone = { x, y, attention: 0, lastSeen: Date.now() };
            zones.push(zone);
        }
        
        zone.attention += 1;
        zone.lastSeen = Date.now();
        
        // Keep only active zones
        this.behaviorTracker.attentionZones = zones.filter(z => 
            Date.now() - z.lastSeen < 5000
        );
    }
    
    triggerAttractionResponse(x, y) {
        // Create visual feedback at click location
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 0;
            height: 0;
            border: 2px solid rgba(0, 255, 136, 0.6);
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
            transform: translate(-50%, -50%);
            animation: rippleExpand 0.6s ease-out;
        `;
        
        // Add ripple animation
        if (!document.getElementById('ripple-animation-style')) {
            const style = document.createElement('style');
            style.id = 'ripple-animation-style';
            style.textContent = `
                @keyframes rippleExpand {
                    0% {
                        width: 0;
                        height: 0;
                        opacity: 0.6;
                    }
                    100% {
                        width: 200px;
                        height: 200px;
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    }
    
    trackElementHover() {
        let hoverStartTime = {};
        
        document.addEventListener('mouseover', (e) => {
            const elementId = e.target.id || e.target.className || 'unknown';
            hoverStartTime[elementId] = Date.now();
        });
        
        document.addEventListener('mouseout', (e) => {
            const elementId = e.target.id || e.target.className || 'unknown';
            if (hoverStartTime[elementId]) {
                const duration = Date.now() - hoverStartTime[elementId];
                this.behaviorTracker.timeOnElements[elementId] = 
                    (this.behaviorTracker.timeOnElements[elementId] || 0) + duration;
            }
        });
    }
    
    initializeAttractionLoops() {
        // Attention Loop
        this.attractionLoops.push({
            name: 'attention',
            interval: setInterval(() => {
                this.enhanceAttentionZones();
            }, 2000)
        });
        
        // Engagement Loop
        this.attractionLoops.push({
            name: 'engagement',
            interval: setInterval(() => {
                this.triggerEngagementCues();
            }, 5000)
        });
        
        // Reward Loop
        this.attractionLoops.push({
            name: 'reward',
            interval: setInterval(() => {
                this.showRewardHints();
            }, 10000)
        });
    }
    
    enhanceAttentionZones() {
        // Enhance visual effects in high-attention zones
        const topZones = this.behaviorTracker.attentionZones
            .sort((a, b) => b.attention - a.attention)
            .slice(0, 3);
        
        topZones.forEach(zone => {
            // Create subtle glow effect
            const glow = document.createElement('div');
            glow.style.cssText = `
                position: fixed;
                left: ${zone.x}px;
                top: ${zone.y}px;
                width: 200px;
                height: 200px;
                background: radial-gradient(circle, rgba(0, 255, 136, 0.1), transparent);
                pointer-events: none;
                z-index: 1;
                transform: translate(-50%, -50%);
                animation: glowPulse 2s ease-in-out infinite;
            `;
            
            if (!document.getElementById('glow-pulse-style')) {
                const style = document.createElement('style');
                style.id = 'glow-pulse-style';
                style.textContent = `
                    @keyframes glowPulse {
                        0%, 100% { opacity: 0.1; transform: translate(-50%, -50%) scale(1); }
                        50% { opacity: 0.3; transform: translate(-50%, -50%) scale(1.2); }
                    }
                `;
                document.head.appendChild(style);
            }
            
            document.body.appendChild(glow);
            setTimeout(() => glow.remove(), 2000);
        });
    }
    
    triggerEngagementCues() {
        // Trigger subtle engagement cues
        const elements = document.querySelectorAll('.btn-battle, .battle-tab, .stat-box');
        elements.forEach((el, index) => {
            setTimeout(() => {
                el.style.transition = 'all 0.3s ease';
                el.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    el.style.transform = 'scale(1)';
                }, 300);
            }, index * 100);
        });
    }
    
    showRewardHints() {
        // Show subtle reward hints
        const hint = document.createElement('div');
        hint.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            padding: 15px 20px;
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(0, 212, 255, 0.2));
            border: 2px solid rgba(0, 255, 136, 0.5);
            border-radius: 10px;
            color: var(--primary);
            font-size: 0.9em;
            z-index: 1000;
            animation: hintFadeInOut 3s ease-in-out;
            pointer-events: none;
        `;
        hint.textContent = '✨ New rewards available!';
        
        if (!document.getElementById('hint-fade-style')) {
            const style = document.createElement('style');
            style.id = 'hint-fade-style';
            style.textContent = `
                @keyframes hintFadeInOut {
                    0%, 100% { opacity: 0; transform: translateY(20px); }
                    20%, 80% { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(hint);
        setTimeout(() => hint.remove(), 3000);
    }
    
    getBehaviorData() {
        return {
            mouseMovements: this.behaviorTracker.mouseMovements.length,
            clicks: this.behaviorTracker.clicks.length,
            scrolls: this.behaviorTracker.scrolls.length,
            attentionZones: this.behaviorTracker.attentionZones.length,
            topElements: Object.entries(this.behaviorTracker.timeOnElements)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([element, time]) => ({ element, time }))
        };
    }
    
    destroy() {
        this.isActive = false;
        this.attractionLoops.forEach(loop => clearInterval(loop.interval));
        document.querySelectorAll('.butterfly-spiral-container, .butterfly-mandala-container, .butterfly-circle-container, .butterfly-gradient-overlay').forEach(el => el.remove());
    }
}

// Global instance
window.butterflyLoopMatrix = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('battle-page') || window.location.pathname.includes('/battle')) {
        window.butterflyLoopMatrix = new ButterflyLoopMatrix('battle-page');
        window.butterflyLoopMatrix.init();
    }
});

