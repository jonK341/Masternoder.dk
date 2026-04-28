/**
 * Template Effects System
 * Provides visual effects, animations, and interactive enhancements
 */
class TemplateEffects {
    constructor() {
        this.activeEffects = new Set();
        this.particleSystems = new Map();
        this.init();
    }

    init() {
        // Initialize on DOM ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEffects());
        } else {
            this.setupEffects();
        }
    }

    setupEffects() {
        // Apply glow effects to primary elements
        this.applyGlowEffects();
        
        // Setup particle systems
        this.setupParticles();
        
        // Setup scroll animations
        this.setupScrollAnimations();
        
        // Setup hover effects
        this.setupHoverEffects();
        
        // Setup typing effects
        this.setupTypingEffects();
    }

    // Glow effects for buttons and cards
    applyGlowEffects() {
        const glowElements = document.querySelectorAll('.glow-effect, .button, .card, .stat-card');
        glowElements.forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.style.boxShadow = '0 0 20px rgba(0, 255, 136, 0.5), 0 0 40px rgba(0, 212, 255, 0.3)';
                el.style.transition = 'box-shadow 0.3s ease';
            });
            el.addEventListener('mouseleave', () => {
                el.style.boxShadow = '';
            });
        });
    }

    // Particle system for backgrounds
    setupParticles() {
        const particleContainers = document.querySelectorAll('.particle-container, body');
        particleContainers.forEach(container => {
            if (container.classList.contains('particles-enabled')) {
                this.createParticleSystem(container);
            }
        });
    }

    createParticleSystem(container) {
        const canvas = document.createElement('canvas');
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '0';
        container.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const particleCount = 50;

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.speedY = Math.random() * 0.5 - 0.25;
                this.opacity = Math.random() * 0.5 + 0.2;
            }

            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                if (this.x > canvas.width) this.x = 0;
                if (this.x < 0) this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                if (this.y < 0) this.y = canvas.height;
            }

            draw() {
                ctx.fillStyle = `rgba(0, 255, 136, ${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(particle => {
                particle.update();
                particle.draw();
            });
            requestAnimationFrame(animate);
        };

        animate();

        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });

        this.particleSystems.set(container, { canvas, particles, animate });
    }

    // Scroll animations
    setupScrollAnimations() {
        const animatedElements = document.querySelectorAll('.fade-in, .slide-in, .scale-in');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        animatedElements.forEach(el => observer.observe(el));
    }

    // Hover effects
    setupHoverEffects() {
        const hoverElements = document.querySelectorAll('.hover-lift, .hover-scale, .hover-rotate');
        
        hoverElements.forEach(el => {
            el.addEventListener('mouseenter', () => {
                if (el.classList.contains('hover-lift')) {
                    el.style.transform = 'translateY(-5px)';
                } else if (el.classList.contains('hover-scale')) {
                    el.style.transform = 'scale(1.05)';
                } else if (el.classList.contains('hover-rotate')) {
                    el.style.transform = 'rotate(5deg)';
                }
            });
            
            el.addEventListener('mouseleave', () => {
                el.style.transform = '';
            });
        });
    }

    // Typing effect for text
    setupTypingEffects() {
        const typingElements = document.querySelectorAll('.typing-effect');
        
        typingElements.forEach(el => {
            const text = el.textContent;
            el.textContent = '';
            el.style.borderRight = '2px solid rgba(0, 255, 136, 0.8)';
            
            let index = 0;
            const type = () => {
                if (index < text.length) {
                    el.textContent += text.charAt(index);
                    index++;
                    setTimeout(type, 50);
                } else {
                    el.style.borderRight = 'none';
                }
            };
            
            type();
        });
    }

    // Pulse effect
    pulse(element, duration = 1000) {
        element.style.animation = `pulse ${duration}ms ease-in-out`;
        setTimeout(() => {
            element.style.animation = '';
        }, duration);
    }

    // Shake effect
    shake(element, intensity = 10) {
        const originalTransform = element.style.transform;
        let currentIntensity = intensity;
        const shakeInterval = setInterval(() => {
            const x = (Math.random() - 0.5) * currentIntensity;
            const y = (Math.random() - 0.5) * currentIntensity;
            element.style.transform = `translate(${x}px, ${y}px)`;
            currentIntensity *= 0.9;
            
            if (currentIntensity < 0.5) {
                clearInterval(shakeInterval);
                element.style.transform = originalTransform;
            }
        }, 20);
    }

    // Gradient animation
    animateGradient(element, colors, duration = 3000) {
        let currentIndex = 0;
        const animate = () => {
            const nextIndex = (currentIndex + 1) % colors.length;
            element.style.background = `linear-gradient(135deg, ${colors[currentIndex]}, ${colors[nextIndex]})`;
            currentIndex = nextIndex;
        };
        
        setInterval(animate, duration);
    }

    // Ripple effect
    createRipple(event, element) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
}

// Initialize effects
window.templateEffects = new TemplateEffects();
