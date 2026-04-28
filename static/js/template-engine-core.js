/**
 * Template Engine Core
 * Main template engine that integrates all template features
 */
class TemplateEngineCore {
    constructor(pageId, baseUrl = '') {
        this.pageId = pageId;
        this.baseUrl = baseUrl || window.location.origin;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.activeTemplate = null;
        this.init();
    }

    async init() {
        // Load user's active template
        await this.loadActiveTemplate();
        
        // Apply template
        this.applyTemplate();
        
        // Initialize integrations
        this.initializeIntegrations();
    }

    async loadActiveTemplate() {
        try {
            // Check for user's active template preference
            const response = await fetch(`${this.baseUrl}/api/templates/store/user/${this.userId}/owned`);
            const data = await response.json();
            
            if (data.success && data.templates.length > 0) {
                // Use first owned template or default
                this.activeTemplate = data.templates[0];
            } else {
                // Use default template
                this.activeTemplate = {
                    id: 'professor_a_plus',
                    name: 'Professor A+ Template',
                    theme_css: '/static/css/themes/professor-a-plus.css',
                    effects_js: '/static/js/effects/professor-a-plus-effects.js'
                };
            }
        } catch (error) {
            console.warn('Could not load active template, using default:', error);
            this.activeTemplate = {
                id: 'professor_a_plus',
                name: 'Professor A+ Template',
                theme_css: '/static/css/themes/professor-a-plus.css',
                effects_js: '/static/js/effects/professor-a-plus-effects.js'
            };
        }
    }

    applyTemplate() {
        if (!this.activeTemplate) return;

        // Apply CSS theme
        if (this.activeTemplate.theme_css) {
            this.loadCSS(this.activeTemplate.theme_css);
        }

        // Load JavaScript effects
        if (this.activeTemplate.effects_js) {
            this.loadJS(this.activeTemplate.effects_js);
        }

        // Add template class to body
        document.body.classList.add(`template-${this.activeTemplate.id.replace(/_/g, '-')}`);
    }

    loadCSS(href) {
        if (!href) return;
        
        // Check if already loaded
        const existing = document.querySelector(`link[href="${href}"]`);
        if (existing) return;

        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        document.head.appendChild(link);
    }

    loadJS(src) {
        if (!src) return;
        
        // Check if already loaded
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing) return;

        const script = document.createElement('script');
        script.src = src;
        document.body.appendChild(script);
    }

    initializeIntegrations() {
        // Integrate with image support
        if (window.imageSupport) {
            window.imageSupport.applyPageImages(window.location.pathname);
        }

        // Integrate with template effects
        if (window.templateEffects) {
            // Effects are auto-initialized
        }

        // Integrate with template services
        if (window.templateServices) {
            // Services are auto-initialized
        }

        // Integrate with agent skill sets
        if (window.agentSkillSets) {
            // Skill sets are auto-initialized
        }

        // Integrate with bonus template store
        if (window.bonusTemplateStore) {
            // Store is auto-initialized
        }
    }

    async switchTemplate(templateId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/user/${this.userId}/apply/${templateId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload page to apply new template
                window.location.reload();
            } else {
                console.error('Failed to switch template:', data.error);
            }
        } catch (error) {
            console.error('Error switching template:', error);
        }
    }
}

// Initialize template engine on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const pageId = document.body.dataset.pageId || window.location.pathname.replace(/\//g, '_');
        window.templateEngine = new TemplateEngineCore(pageId);
    });
} else {
    const pageId = document.body.dataset.pageId || window.location.pathname.replace(/\//g, '_');
    window.templateEngine = new TemplateEngineCore(pageId);
}
