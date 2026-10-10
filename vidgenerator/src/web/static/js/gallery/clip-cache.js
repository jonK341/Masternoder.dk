/**
 * Clip Cache Manager - Store clips in browser cache
 * Implements max clips limit and browser storage
 */

class ClipCacheManager {
    constructor() {
        this.STORAGE_KEY = 'documentary_clips_cache';
        this.MAX_CLIPS = 50; // Maximum clips to store
        this.MAX_SIZE_MB = 100; // Maximum cache size in MB
        this.cache = this.loadCache();
    }

    /**
     * Load cache from localStorage
     */
    loadCache() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const cache = JSON.parse(stored);
                // Validate cache structure
                if (cache && cache.clips && Array.isArray(cache.clips)) {
                    return cache;
                }
            }
        } catch (e) {
            console.warn('Failed to load clip cache:', e);
        }
        return {
            clips: [],
            metadata: {
                lastUpdated: Date.now(),
                version: '1.0'
            }
        };
    }

    /**
     * Save cache to localStorage
     */
    saveCache() {
        try {
            this.cache.metadata.lastUpdated = Date.now();
            const json = JSON.stringify(this.cache);
            const sizeMB = new Blob([json]).size / (1024 * 1024);
            
            if (sizeMB > this.MAX_SIZE_MB) {
                console.warn(`Cache size (${sizeMB.toFixed(2)}MB) exceeds limit (${this.MAX_SIZE_MB}MB), cleaning...`);
                this.cleanupCache();
                return this.saveCache(); // Retry after cleanup
            }
            
            localStorage.setItem(this.STORAGE_KEY, json);
            return true;
        } catch (e) {
            console.warn('Failed to save clip cache:', e);
            // If quota exceeded, cleanup and retry
            if (e.name === 'QuotaExceededError') {
                this.cleanupCache();
                try {
                    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.cache));
                    return true;
                } catch (e2) {
                    console.error('Failed to save cache after cleanup:', e2);
                }
            }
            return false;
        }
    }

    /**
     * Add or update a clip in cache
     */
    addClip(clipData) {
        if (!clipData || !clipData.id) {
            console.warn('Invalid clip data');
            return false;
        }

        // Remove existing clip with same ID
        this.cache.clips = this.cache.clips.filter(c => c.id !== clipData.id);

        // Add new clip
        this.cache.clips.push({
            ...clipData,
            cachedAt: Date.now()
        });

        // Enforce max clips limit
        if (this.cache.clips.length > this.MAX_CLIPS) {
            // Remove oldest clips
            this.cache.clips.sort((a, b) => (a.cachedAt || 0) - (b.cachedAt || 0));
            this.cache.clips = this.cache.clips.slice(-this.MAX_CLIPS);
        }

        return this.saveCache();
    }

    /**
     * Get clip from cache
     */
    getClip(clipId) {
        return this.cache.clips.find(c => c.id === clipId);
    }

    /**
     * Get all clips
     */
    getAllClips() {
        return this.cache.clips;
    }

    /**
     * Remove clip from cache
     */
    removeClip(clipId) {
        this.cache.clips = this.cache.clips.filter(c => c.id !== clipId);
        return this.saveCache();
    }

    /**
     * Cleanup cache - remove old or unused clips
     */
    cleanupCache() {
        const now = Date.now();
        const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days

        // Remove clips older than maxAge
        this.cache.clips = this.cache.clips.filter(clip => {
            const age = now - (clip.cachedAt || 0);
            return age < maxAge;
        });

        // If still over limit, remove oldest
        if (this.cache.clips.length > this.MAX_CLIPS) {
            this.cache.clips.sort((a, b) => (a.cachedAt || 0) - (b.cachedAt || 0));
            this.cache.clips = this.cache.clips.slice(-this.MAX_CLIPS);
        }

        return this.saveCache();
    }

    /**
     * Clear all cache
     */
    clearCache() {
        this.cache = {
            clips: [],
            metadata: {
                lastUpdated: Date.now(),
                version: '1.0'
            }
        };
        localStorage.removeItem(this.STORAGE_KEY);
    }

    /**
     * Get cache stats
     */
    getStats() {
        const size = new Blob([JSON.stringify(this.cache)]).size;
        return {
            clipCount: this.cache.clips.length,
            maxClips: this.MAX_CLIPS,
            sizeMB: (size / (1024 * 1024)).toFixed(2),
            maxSizeMB: this.MAX_SIZE_MB,
            lastUpdated: new Date(this.cache.metadata.lastUpdated).toLocaleString()
        };
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClipCacheManager;
} else {
    window.ClipCacheManager = ClipCacheManager;
}


