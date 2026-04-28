/**
 * Game Sounds System - Victory sounds and progress feedback
 */
class GameSounds {
    constructor() {
        this.sounds = {};
        this.enabled = true;
        this.volume = 0.7;
        this.init();
    }

    init() {
        // Create audio context for sound generation
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('[GameSounds] AudioContext not supported');
            this.enabled = false;
        }
    }

    playVictorySound() {
        if (!this.enabled || !this.audioContext) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Victory melody: ascending notes
            const notes = [523.25, 659.25, 783.99, 1046.50]; // C, E, G, C
            let currentNote = 0;
            
            const playNote = (freq, duration) => {
                const osc = this.audioContext.createOscillator();
                const gain = this.audioContext.createGain();
                
                osc.connect(gain);
                gain.connect(this.audioContext.destination);
                
                osc.frequency.value = freq;
                osc.type = 'sine';
                
                gain.gain.setValueAtTime(0, this.audioContext.currentTime);
                gain.gain.linearRampToValueAtTime(this.volume * 0.3, this.audioContext.currentTime + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
                
                osc.start(this.audioContext.currentTime);
                osc.stop(this.audioContext.currentTime + duration);
            };
            
            notes.forEach((freq, index) => {
                setTimeout(() => playNote(freq, 0.2), index * 150);
            });
        } catch (e) {
            console.warn('[GameSounds] Error playing victory sound:', e);
        }
    }

    playProgressSound(progress) {
        if (!this.enabled || !this.audioContext) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Progress sound: frequency based on progress
            const baseFreq = 200 + (progress * 400); // 200-600 Hz
            
            oscillator.frequency.value = baseFreq;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(this.volume * 0.2, this.audioContext.currentTime + 0.01);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.1);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 0.1);
        } catch (e) {
            console.warn('[GameSounds] Error playing progress sound:', e);
        }
    }

    playAchievementSound() {
        if (!this.enabled || !this.audioContext) return;
        
        try {
            // Achievement sound: fanfare
            const notes = [523.25, 659.25, 783.99, 1046.50, 1318.51];
            notes.forEach((freq, index) => {
                setTimeout(() => {
                    const osc = this.audioContext.createOscillator();
                    const gain = this.audioContext.createGain();
                    
                    osc.connect(gain);
                    gain.connect(this.audioContext.destination);
                    
                    osc.frequency.value = freq;
                    osc.type = 'triangle';
                    
                    gain.gain.setValueAtTime(0, this.audioContext.currentTime);
                    gain.gain.linearRampToValueAtTime(this.volume * 0.4, this.audioContext.currentTime + 0.05);
                    gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3);
                    
                    osc.start(this.audioContext.currentTime);
                    osc.stop(this.audioContext.currentTime + 0.3);
                }, index * 100);
            });
        } catch (e) {
            console.warn('[GameSounds] Error playing achievement sound:', e);
        }
    }

    playItemSound() {
        if (!this.enabled || !this.audioContext) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(this.volume * 0.3, this.audioContext.currentTime + 0.05);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.2);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 0.2);
        } catch (e) {
            console.warn('[GameSounds] Error playing item sound:', e);
        }
    }

    playArtifactSound() {
        if (!this.enabled || !this.audioContext) return;
        
        try {
            // Artifact discovery: mystical sound
            const frequencies = [440, 554.37, 659.25, 880];
            frequencies.forEach((freq, index) => {
                setTimeout(() => {
                    const osc = this.audioContext.createOscillator();
                    const gain = this.audioContext.createGain();
                    
                    osc.connect(gain);
                    gain.connect(this.audioContext.destination);
                    
                    osc.frequency.value = freq;
                    osc.type = 'sine';
                    
                    gain.gain.setValueAtTime(0, this.audioContext.currentTime);
                    gain.gain.linearRampToValueAtTime(this.volume * 0.5, this.audioContext.currentTime + 0.1);
                    gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5);
                    
                    osc.start(this.audioContext.currentTime);
                    osc.stop(this.audioContext.currentTime + 0.5);
                }, index * 200);
            });
        } catch (e) {
            console.warn('[GameSounds] Error playing artifact sound:', e);
        }
    }

    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
    }

    setEnabled(enabled) {
        this.enabled = enabled;
    }
}

// Initialize game sounds
let gameSounds;
if (typeof window !== 'undefined') {
    gameSounds = new GameSounds();
    window.gameSounds = gameSounds;
}

