/**
 * Theme Sound Manager - Handle theme-specific sounds for clips
 */

class ThemeSoundManager {
    constructor() {
        this.sounds = new Map();
        this.currentTheme = null;
        this.volume = 0.5; // Default volume
        this.enabled = true;
    }

    /**
     * Load theme sound configuration
     */
    loadThemeSound(themeName) {
        const themeSounds = {
            'matrix': {
                ambient: '/static/audio/matrix-ambient.mp3',
                transition: '/static/audio/matrix-transition.mp3',
                success: '/static/audio/matrix-success.mp3'
            },
            'mtg': {
                ambient: '/static/audio/mtg-ambient.mp3',
                transition: '/static/audio/mtg-transition.mp3',
                success: '/static/audio/mtg-success.mp3'
            },
            'cyberpunk': {
                ambient: '/static/audio/cyberpunk-ambient.mp3',
                transition: '/static/audio/cyberpunk-transition.mp3',
                success: '/static/audio/cyberpunk-success.mp3'
            },
            'default': {
                ambient: '/static/audio/default-ambient.mp3',
                transition: '/static/audio/default-transition.mp3',
                success: '/static/audio/default-success.mp3'
            }
        };

        const theme = themeSounds[themeName] || themeSounds['default'];
        this.currentTheme = themeName;
        
        // Preload sounds
        Object.keys(theme).forEach(key => {
            if (!this.sounds.has(`${themeName}-${key}`)) {
                const audio = new Audio(theme[key]);
                audio.volume = this.volume;
                audio.preload = 'auto';
                this.sounds.set(`${themeName}-${key}`, audio);
            }
        });
    }

    /**
     * Play theme sound
     */
    playSound(soundType = 'ambient') {
        if (!this.enabled || !this.currentTheme) {
            return;
        }

        const soundKey = `${this.currentTheme}-${soundType}`;
        const audio = this.sounds.get(soundKey);
        
        if (audio) {
            audio.currentTime = 0;
            audio.volume = this.volume;
            audio.play().catch(err => {
                console.warn('Could not play theme sound:', err);
            });
        }
    }

    /**
     * Stop all sounds
     */
    stopAllSounds() {
        this.sounds.forEach(audio => {
            audio.pause();
            audio.currentTime = 0;
        });
    }

    /**
     * Set volume (0.0 to 1.0)
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        this.sounds.forEach(audio => {
            audio.volume = this.volume;
        });
    }

    /**
     * Enable/disable sounds
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        if (!enabled) {
            this.stopAllSounds();
        }
    }

    /**
     * Get current theme
     */
    getCurrentTheme() {
        return this.currentTheme;
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSoundManager;
} else {
    window.ThemeSoundManager = ThemeSoundManager;
}


