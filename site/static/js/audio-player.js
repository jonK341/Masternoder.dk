/**
 * Audio Player System - Sound Effects and Theme Intro Songs
 * For compelling demons, especially money demons
 */
class AudioPlayer {
    constructor() {
        this.audioElements = new Map();
        this.activeAudio = new Map();
        this.volume = 1.0;
        this.muted = false;
    }
    
    /**
     * Load audio asset
     */
    async loadAudio(audioId, url) {
        if (this.audioElements.has(audioId)) {
            return this.audioElements.get(audioId);
        }
        
        const audio = new Audio(url);
        audio.preload = 'auto';
        this.audioElements.set(audioId, audio);
        return audio;
    }
    
    /**
     * Play audio
     */
    async playAudio(audioId, url, options = {}) {
        try {
            const audio = await this.loadAudio(audioId, url);
            
            // Set options
            audio.volume = options.volume !== undefined ? options.volume : this.volume;
            audio.loop = options.loop || false;
            
            // Play audio
            await audio.play();
            
            // Track active audio
            this.activeAudio.set(audioId, audio);
            
            // Handle end
            audio.onended = () => {
                this.activeAudio.delete(audioId);
            };
            
            return { success: true, audioId };
        } catch (error) {
            console.error('Error playing audio:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Stop audio
     */
    stopAudio(audioId) {
        const audio = this.audioElements.get(audioId);
        if (audio) {
            audio.pause();
            audio.currentTime = 0;
            this.activeAudio.delete(audioId);
            return { success: true };
        }
        return { success: false, error: 'Audio not found' };
    }
    
    /**
     * Stop all audio
     */
    stopAll() {
        this.activeAudio.forEach((audio, audioId) => {
            audio.pause();
            audio.currentTime = 0;
        });
        this.activeAudio.clear();
    }
    
    /**
     * Set volume
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        this.audioElements.forEach(audio => {
            audio.volume = this.volume;
        });
    }
    
    /**
     * Mute/unmute
     */
    setMuted(muted) {
        this.muted = muted;
        this.audioElements.forEach(audio => {
            audio.muted = muted;
        });
    }
    
    /**
     * Play demon compelling audio (especially money demon)
     */
    async playDemonCompelling(demonType = 'money') {
        try {
            const response = await fetch(`/api/audio/demon-compelling?demon_type=${demonType}`);
            const data = await response.json();
            
            if (data.success && data.demon_audio.length > 0) {
                const audio = data.demon_audio[0]; // Play first available
                return await this.playAudio(audio.id, audio.url, { loop: true });
            }
            
            return { success: false, error: 'No demon compelling audio found' };
        } catch (error) {
            console.error('Error playing demon compelling audio:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Play theme intro
     */
    async playThemeIntro(themeName) {
        try {
            const response = await fetch('/api/audio/theme-intros');
            const data = await response.json();
            
            if (data.success && data.theme_intros.length > 0) {
                const intro = data.theme_intros.find(t => themeName.toLowerCase() in t.name.toLowerCase()) || data.theme_intros[0];
                return await this.playAudio(intro.id, intro.url);
            }
            
            return { success: false, error: 'No theme intro found' };
        } catch (error) {
            console.error('Error playing theme intro:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Play sound effect
     */
    async playSoundEffect(effectName) {
        try {
            const response = await fetch('/api/audio/type/sound_effect');
            const data = await response.json();
            
            if (data.success && data.audio.length > 0) {
                const effect = data.audio.find(a => effectName.toLowerCase() in a.name.toLowerCase()) || data.audio[0];
                return await this.playAudio(effect.id, effect.url);
            }
            
            return { success: false, error: 'Sound effect not found' };
        } catch (error) {
            console.error('Error playing sound effect:', error);
            return { success: false, error: error.message };
        }
    }
}

// Global audio player instance
const audioPlayer = new AudioPlayer();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioPlayer;
}

