/**
 * Theme Toggle Component
 * Allows users to switch between dark and light themes
 */

class ThemeToggle {
    constructor() {
        this.currentTheme = this.getStoredTheme() || 'dark';
        this.init();
    }
    
    init() {
        // Apply stored theme
        this.applyTheme(this.currentTheme);
        
        // Create toggle button if not exists
        this.createToggleButton();
        
        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.applyTheme(e.matches ? 'light' : 'dark');
                }
            });
        }
    }
    
    createToggleButton() {
        // Check if button already exists
        if (document.getElementById('theme-toggle-btn')) {
            return;
        }
        
        const button = document.createElement('button');
        button.id = 'theme-toggle-btn';
        button.className = 'theme-toggle-btn';
        button.innerHTML = this.currentTheme === 'dark' 
            ? '<i class="fas fa-sun"></i>' 
            : '<i class="fas fa-moon"></i>';
        button.title = `Switch to ${this.currentTheme === 'dark' ? 'light' : 'dark'} theme`;
        button.setAttribute('aria-label', 'Toggle theme');
        
        button.addEventListener('click', () => {
            this.toggle();
        });
        
        // Add to page (try to find a good location)
        const nav = document.querySelector('.page-nav .nav-container');
        if (nav) {
            nav.appendChild(button);
        } else {
            // Fallback: add to body
            document.body.insertBefore(button, document.body.firstChild);
        }
    }
    
    toggle() {
        this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.currentTheme);
        this.storeTheme(this.currentTheme);
        this.updateButton();
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.body.classList.toggle('light-theme', theme === 'light');
        document.body.classList.toggle('dark-theme', theme === 'dark');
        
        // Update CSS variables if needed
        if (theme === 'light') {
            document.documentElement.style.setProperty('--bg-primary', '#ffffff');
            document.documentElement.style.setProperty('--bg-secondary', '#f5f5f5');
            document.documentElement.style.setProperty('--bg-card', '#ffffff');
            document.documentElement.style.setProperty('--text-primary', '#1a1a1a');
            document.documentElement.style.setProperty('--text-secondary', '#666666');
            document.documentElement.style.setProperty('--border-primary', '#e0e0e0');
        } else {
            // Reset to default dark theme
            document.documentElement.style.removeProperty('--bg-primary');
            document.documentElement.style.removeProperty('--bg-secondary');
            document.documentElement.style.removeProperty('--bg-card');
            document.documentElement.style.removeProperty('--text-primary');
            document.documentElement.style.removeProperty('--text-secondary');
            document.documentElement.style.removeProperty('--border-primary');
        }
    }
    
    updateButton() {
        const button = document.getElementById('theme-toggle-btn');
        if (button) {
            button.innerHTML = this.currentTheme === 'dark' 
                ? '<i class="fas fa-sun"></i>' 
                : '<i class="fas fa-moon"></i>';
            button.title = `Switch to ${this.currentTheme === 'dark' ? 'light' : 'dark'} theme`;
        }
    }
    
    getStoredTheme() {
        try {
            return localStorage.getItem('theme-preference');
        } catch (e) {
            return null;
        }
    }
    
    storeTheme(theme) {
        try {
            localStorage.setItem('theme-preference', theme);
        } catch (e) {
            console.warn('Could not store theme preference:', e);
        }
    }
}

// Initialize theme toggle on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.themeToggle = new ThemeToggle();
    });
} else {
    window.themeToggle = new ThemeToggle();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeToggle;
}

